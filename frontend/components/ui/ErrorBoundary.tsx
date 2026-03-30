"use client";

import { Component, type ReactNode } from "react";

type Props = Readonly<{ children: ReactNode; fallback?: ReactNode }>;
type State = { hasError: boolean; message: string };

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : "Erreur inconnue";
    return { hasError: true, message };
  }

  override componentDidCatch(error: unknown, info: { componentStack?: string | null }) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  override render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500">
            <p className="font-medium mb-1">Une erreur inattendue s&apos;est produite.</p>
            <p className="text-xs opacity-70">{this.state.message}</p>
            <button
              onClick={() => this.setState({ hasError: false, message: "" })}
              className="mt-4 px-4 py-2 text-sm bg-accent text-white rounded-lg hover:opacity-90"
            >
              Réessayer
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
