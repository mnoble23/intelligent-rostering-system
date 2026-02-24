import "./Login.css";

interface AuthChoiceProps {
  isBootstrapped: boolean;
  onSelectLogin: () => void;
  onSelectCreate: () => void;
}

export default function AuthChoice({ isBootstrapped, onSelectLogin, onSelectCreate }: AuthChoiceProps) {
  return (
    <main className="login-page">
      <section className="login-page__card auth-choice">
        <h1>Roster OS</h1>
        <p>Choose how you want to continue.</p>

        <div className="auth-choice__actions">
          <button type="button" onClick={onSelectLogin}>Sign In To Existing Workplace</button>
          <button type="button" onClick={onSelectCreate} disabled={isBootstrapped}>Create New Workplace</button>
        </div>

        {isBootstrapped && (
          <p className="auth-choice__hint">
            A workplace already exists for this deployment, so creation is disabled.
          </p>
        )}
      </section>
    </main>
  );
}
