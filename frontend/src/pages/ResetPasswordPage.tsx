import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { resetPassword } from "../api/auth";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);

    if (!token) {
      setError("This reset link is missing its token.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setIsSubmitting(true);

    try {
      await resetPassword(token, newPassword);
      setIsSubmitted(true);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to reset password",
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
          <h1>Reset password</h1>
          <p className="muted">Choose a new password for your account.</p>
        </div>

        {!token ? (
          <div className="alert">
            This reset link is invalid or missing its token. Request a
            new one from the{" "}
            <Link to="/forgot-password">forgot password</Link> page.
          </div>
        ) : isSubmitted ? (
          <p className="muted">
            Your password has been reset.{" "}
            <Link to="/login">Log in</Link> with your new password.
          </p>
        ) : (
          <>
            {error ? <div className="alert">{error}</div> : null}

            <form className="form-grid" onSubmit={handleSubmit}>
              <label>
                New password
                <input
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  required
                  minLength={12}
                  maxLength={128}
                />
                <span className="field-hint">
                  Use at least 12 characters.
                </span>
              </label>

              <label>
                Confirm new password
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(event.target.value)
                  }
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
                {isSubmitting ? "Resetting..." : "Reset password"}
              </button>
            </form>
          </>
        )}

        <p className="auth-switch">
          <Link to="/login">Back to log in</Link>
        </p>
      </section>
    </main>
  );
}
