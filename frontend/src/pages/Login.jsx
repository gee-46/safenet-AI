import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button, Field, inputClass } from "../components/ui/Primitives";
import { ShieldCheck, Mail, Lock, Phone, UserCircle, Globe2 } from "lucide-react";

export default function Login() {
  const { login, register, error: authError } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({
    email: "",
    password: "",
    phone: "",
    role: "citizen",
    language_preference: "en",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const cleanPhone = (val) => {
    let clean = val.replace(/\s+/g, "");
    if (/^[1-9]\d{9}$/.test(clean)) {
      return "+91" + clean;
    }
    return clean;
  };

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (isRegister) {
        const formattedPhone = cleanPhone(form.phone);
        if (!/^\+?[1-9]\d{9,14}$/.test(formattedPhone)) {
          throw new Error("Enter a valid phone number (e.g. +919999999999 or 10-digit number).");
        }
        await register(form.email, formattedPhone, form.password, form.role, form.language_preference);
      } else {
        await login(form.email, form.password);
      }
      navigate("/console");
    } catch (err) {
      setError(err?.message || "Authentication failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const update = (key) => (e) => {
    setForm({ ...form, [key]: e.target.value });
  };

  return (
    <div className="flex min-h-[85vh] items-center justify-center bg-void px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-void-line bg-void-surface/50 p-8 backdrop-blur-md shadow-2xl">
        <div className="text-center">
          <div className="flex justify-center">
            <svg width="40" height="40" viewBox="0 0 100 100" className="shrink-0 animate-pulse">
              <polygon
                points="50,4 90,25 90,60 50,96 10,60 10,25"
                fill="none"
                stroke="#FF5A36"
                strokeWidth="6"
              />
              <circle cx="50" cy="45" r="9" fill="#FF5A36" />
            </svg>
          </div>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-ink">
            {isRegister ? "Create Command Account" : "Access Command Console"}
          </h2>
          <p className="mt-2 text-xs uppercase tracking-widest text-ink-faint">
            {isRegister ? "Register for SafeNet AI intelligence" : "Authorized Personnel Access Only"}
          </p>
        </div>

        <form className="mt-8 space-y-4" onSubmit={submit}>
          <Field label="Email Address" required>
            <div className="relative">
              <input
                type="email"
                required
                className={`${inputClass} pl-10`}
                placeholder="officer@safenet.gov.in"
                value={form.email}
                onChange={update("email")}
              />
              <Mail className="absolute left-3.5 top-3.5 h-4 w-4 text-ink-faint" />
            </div>
          </Field>

          {isRegister && (
            <Field label="Phone Number" required hint="e.g. +91 99999 99999">
              <div className="relative">
                <input
                  type="tel"
                  required
                  className={`${inputClass} pl-10`}
                  placeholder="+919876543210"
                  value={form.phone}
                  onChange={update("phone")}
                />
                <Phone className="absolute left-3.5 top-3.5 h-4 w-4 text-ink-faint" />
              </div>
            </Field>
          )}

          <Field label="Password" required hint="Min 8 characters">
            <div className="relative">
              <input
                type="password"
                required
                minLength={8}
                className={`${inputClass} pl-10`}
                placeholder="••••••••"
                value={form.password}
                onChange={update("password")}
              />
              <Lock className="absolute left-3.5 top-3.5 h-4 w-4 text-ink-faint" />
            </div>
          </Field>

          {isRegister && (
            <div className="grid grid-cols-2 gap-4">
              <Field label="Console Role">
                <div className="relative">
                  <select
                    className={`${inputClass} pl-10`}
                    value={form.role}
                    onChange={update("role")}
                  >
                    <option value="citizen">Citizen</option>
                    <option value="officer">Officer</option>
                    <option value="analyst">Analyst</option>
                    <option value="admin">Administrator</option>
                  </select>
                  <UserCircle className="absolute left-3.5 top-3.5 h-4 w-4 text-ink-faint" />
                </div>
              </Field>

              <Field label="Language preference">
                <div className="relative">
                  <select
                    className={`${inputClass} pl-10`}
                    value={form.language_preference}
                    onChange={update("language_preference")}
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="ta">Tamil</option>
                    <option value="te">Telugu</option>
                    <option value="kn">Kannada</option>
                    <option value="ml">Malayalam</option>
                  </select>
                  <Globe2 className="absolute left-3.5 top-3.5 h-4 w-4 text-ink-faint" />
                </div>
              </Field>
            </div>
          )}

          {(error || authError) && (
            <div className="rounded-lg border border-signal-dim bg-signal-dim/10 p-3 text-xs text-signal-soft">
              {error || authError}
            </div>
          )}

          <Button type="submit" loading={loading} icon={ShieldCheck} className="w-full justify-center">
            {isRegister ? "Complete Registration" : "Authenticate Session"}
          </Button>
        </form>

        <div className="text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
            }}
            className="font-mono text-xs uppercase tracking-wider text-ink-dim transition-colors hover:text-ink"
          >
            {isRegister ? "Already registered? Sign In" : "Need command access? Register"}
          </button>
        </div>
      </div>
    </div>
  );
}
