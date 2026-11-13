import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("GradeMatrix Uncaught Error:", error, errorInfo);
  }

  public override render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "#0f172a",
            color: "#f8fafc",
            fontFamily: "Inter, system-ui, sans-serif",
            padding: "20px",
            textAlign: "center",
          }}
        >
          <h2 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>
            Something went wrong
          </h2>
          <p
            style={{
              color: "#94a3b8",
              maxWidth: "500px",
              marginBottom: "1.5rem",
              fontSize: "0.95rem",
            }}
          >
            {this.state.error?.message ||
              "An unexpected error occurred while rendering the page."}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: "#4f46e5",
              color: "#fff",
              border: "none",
              padding: "10px 24px",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.95rem",
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
