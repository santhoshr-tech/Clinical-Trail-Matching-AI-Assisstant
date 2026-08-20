import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserRole, UserProfile } from '../types';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  login: (email: string, role: UserRole) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (allowedRoles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('cra_user_session');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    // Default active user session for prototype development
    return {
      id: '00000000-0000-0000-0000-000000000002',
      email: 'coordinator@clinicaltrial.ai',
      fullName: 'Dr. Sarah Connor (CRC)',
      role: 'research_coordinator',
    };
  });

  const login = async (email: string, role: UserRole) => {
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role }),
      });
      const data = await res.json();
      if (data.success && data.data?.user) {
        const newUser: UserProfile = {
          id: data.data.user.id,
          email: data.data.user.email,
          fullName: data.data.user.fullName,
          role: data.data.user.role as UserRole,
        };
        setUser(newUser);
        localStorage.setItem('cra_user_session', JSON.stringify(newUser));
      }
    } catch (err) {
      console.error('Login error:', err);
      // Fallback update
      const newUser: UserProfile = {
        id: '00000000-0000-0000-0000-000000000002',
        email,
        fullName: `User (${role})`,
        role,
      };
      setUser(newUser);
      localStorage.setItem('cra_user_session', JSON.stringify(newUser));
    }
  };

  const logout = async () => {
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        headers: {
          'X-User-Email': user?.email || '',
          'X-User-Role': user?.role || '',
        },
      });
    } catch (e) {
      console.error('Logout audit call error:', e);
    } finally {
      setUser(null);
      localStorage.removeItem('cra_user_session');
    }
  };

  const hasRole = (allowedRoles: UserRole[]) => {
    if (!user) return false;
    return allowedRoles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        logout,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
