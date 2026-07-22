import React, { createContext, useContext } from "react";

const AuthContext = createContext(null);

export const ACCESS_TOKEN_KEY = "safenet_access_token";
export const REFRESH_TOKEN_KEY = "safenet_refresh_token";

const mockUser = {
  email: "officer@safenet.gov.in",
  role: "officer",
};

export function AuthProvider({ children }) {
  const value = {
    user: mockUser,
    loading: false,
    error: null,
    login: async (email, password) => {
      console.log("Mock login called with:", email, password);
    },
    register: async (email, phone, password, role, lang) => {
      console.log("Mock register called with:", email, phone, password, role, lang);
    },
    logout: () => {
      console.log("Mock logout called");
    },
    isLoggedIn: true,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    return {
      user: mockUser,
      loading: false,
      error: null,
      login: async () => {},
      register: async () => {},
      logout: () => {},
      isLoggedIn: true,
    };
  }
  return context;
}
