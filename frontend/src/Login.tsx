import { useState } from "react";
import { Loader2, LockKeyhole } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/api";
import { useLogin } from "@/queries";

export default function Login() {
  const [password, setPassword] = useState("");
  const login = useLogin();

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!password) return;
    login.mutate(password);
  }

  const err = login.error;
  const message =
    err instanceof ApiError && err.status === 401
      ? "Wrong password."
      : err instanceof ApiError && err.status === 429
        ? "Too many attempts. Wait a minute."
        : err
          ? "Could not sign in."
          : null;

  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-5 rounded-xl border bg-card p-6 shadow-sm"
      >
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <LockKeyhole className="h-5 w-5 text-muted-foreground" />
            <h1 className="text-lg font-semibold tracking-tight">easy-notes</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Enter your password to continue.
          </p>
        </div>

        <Input
          type="password"
          autoFocus
          autoComplete="current-password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-label="Password"
          aria-invalid={!!message}
        />

        {message && (
          <p role="alert" className="text-sm text-red-400">
            {message}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={!password || login.isPending}>
          {login.isPending ? (
            <>
              <Loader2 className="animate-spin" /> Signing in…
            </>
          ) : (
            "Sign in"
          )}
        </Button>
      </form>
    </div>
  );
}
