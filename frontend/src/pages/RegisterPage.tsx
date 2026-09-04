import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

import {
  loginUser,
  registerUser,
} from "../api/auth";


export default function RegisterPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [searchParams] = useSearchParams();
  const invitedEmail = searchParams.get("email") ?? "";

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState(invitedEmail);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setIsSubmitting(true);

    try {
      await registerUser({
        email,
        password,
        display_name: displayName,
      });

      await loginUser({
        email,
        password,
      });

      await refreshUser();
      navigate("/", { replace: true });
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to create account",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div>
          <p className="eyebrow">TripSplit Ledger</p>
          <h1>Create account</h1>
          <p className="muted">
            {invitedEmail
              ? "You've been invited to a trip — create your account to join."
              : "Register to create and manage shared trips."}
          </p>
        </div>

        {error ? <div className="alert">{error}</div> : null}

        <form
          className="form-grid"
          onSubmit={handleSubmit}
        >
          <label>
            Display name
            <input
              type="text"
              autoComplete="name"
              value={displayName}
              onChange={(event) => {
                setDisplayName(event.target.value);
              }}
              required
              maxLength={100}
            />
          </label>

          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
              }}
              required
              minLength={12}
              maxLength={128}
            />
            <span className="field-hint">
              Use at least 12 characters.
            </span>
          </label>

          <label>
            Confirm password
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => {
                setConfirmPassword(event.target.value);
              }}
              required
              minLength={12}
              maxLength={128}
            />
          </label>

          <button
            className="primary-button"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? "Creating account..."
              : "Create account"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{" "}
          <Link to="/login">Log in</Link>
        </p>
      </section>
    </main>
  );
}