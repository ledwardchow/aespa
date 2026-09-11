import { Component } from "react";

export class RouteErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="content scroll-content" role="alert">
        <h1>This page could not be loaded</h1>
        <p>Your saved data is unchanged. Reload the page to try again.</p>
        <button className="btn" onClick={() => window.location.reload()}>
          Reload page
        </button>
        <a className="btn secondary" href="#/">
          Return to Sites
        </a>
      </div>
    );
  }
}
