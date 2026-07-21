import React, { createContext, useContext, useEffect, useState } from "react";
import { client } from "../lib/api";

const AuthContext = createContext(null);

export const ACCESS_TOKEN_KEY = "safenet_access_token";
export const REFRESH_TOKEN_KEY = "safenet_refresh_token";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const token = localStorage.getItem(ACCESS_TOKEN_KEY);
        if (!token) {
          setUser(null);
          setLoading(false);
          return;
        }
        const { data } = await client.get("/auth/me");
        setUser(data);
      } catch (err) {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, []);

  async function login(email, password) {
    setError(null);
    try {
      const { data } = await client.post("/auth/login", { email, password });
      localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      
      const { data: profile } = await client.get("/auth/me");
      setUser(profile);
    } catch (err) {
      setError(err?.message || "Login failed");
      throw err;
    }
  }

  async function register(email, phone, password, role = "citizen", languagePreference = "en") {
    setError(null);
    try {
      await client.post("/auth/register", {
        email,
        phone,
        password,
        role,
        language_preference: languagePreference,
      });
      await login(email, password);
    } catch (err) {
      setError(err?.message || "Registration failed");
      throw err;
    }
  }

  function logout() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout, isLoggedIn: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
