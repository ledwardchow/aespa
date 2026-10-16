from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.db import set_engine
from aespa.models import CrawledPage, PageOwaspTest, Site, TestRun
from aespa.services import web_workprogram as workprogram
from aespa.services.recon_summary import _build_page_access
from aespa.services.route_sampling import RouteSampler
from aespa.services.scanner import _exercised_coverage_progress
from aespa.services.specialist_handoffs import handoff_fingerprint

links = [dict(url=f'https://shop.test/users/{i}?account_id=1', depth=1, parent_id=1, incoming_action={}) for i in range(100, 110)]
links.append(dict(url='https://shop.test/users/100?account_id=2', depth=1, parent_id=1, incoming_action={}))
sampler = RouteSampler()
queue = sampler.offer(links, 'alice')
visited = []
while queue:
    item = queue.pop(0)
    visited.append(item['url'])
    queue.extend(sampler.observe(item['url'], {'kind':'page','layout':[len(visited)],'size':1}, 'alice'))
output = {'query_variant': {'discovered':len(links),'visited':len(visited),'account2_visited':any(u.endswith('account_id=2') for u in visited),'drain':sampler.drain('alice')}}
pages = [CrawledPage(id=1,test_run_id=1,url='https://target.test/orders/101',req_auth=True,accessible_by='[11]'), CrawledPage(id=2,test_run_id=1,url='https://target.test/orders/202',req_auth=False,accessible_by='[22]')]
output['access'] = {}
for label, ordered in [('private_then_public',pages),('public_then_private',list(reversed(pages)))]:
    access,_ = _build_page_access(ordered,[],{})
    output['access'][label] = {k:{'anonymous':v['anonymous'],'credential_ids':sorted(v['credential_ids'])} for k,v in access.items()}
output['query_handoff_collision'] = handoff_fingerprint('idor','https://target.test/orders?id=101',session_label='alice') == handoff_fingerprint('idor','https://target.test/orders?id=202',session_label='alice')
engine=create_engine('sqlite:///:memory:',connect_args={'check_same_thread':False},poolclass=StaticPool)
SQLModel.metadata.create_all(engine)
set_engine(engine)
workprogram.get_engine=lambda:engine
with Session(engine) as session:
    site=Site(name='probe',base_url='https://target.test');session.add(site);session.flush()
    run=TestRun(site_id=site.id,name='probe');session.add(run);session.flush();run_id=run.id
    for item,status in [(101,'covered'),(202,'not_started')]:
        page=CrawledPage(test_run_id=run_id,url=f'https://target.test/orders/{item}',in_scope=True,status='crawled',has_object_ref=True)
        session.add(page);session.flush();session.add(PageOwaspTest(test_run_id=run_id,page_id=page.id,owasp_category='A01',status=status))
    session.commit()
matrix=workprogram.get_web_coverage_matrix(run_id)
output['coverage']={'standard':_exercised_coverage_progress(matrix['column_totals'],60),'raw':workprogram.get_web_coverage_gaps(run_id)['totals']}
path=Path('/private/tmp/aespa-grouped-fix-baseline/probe.json');path.write_text(json.dumps(output,indent=2))
print(json.dumps(output,indent=2))
