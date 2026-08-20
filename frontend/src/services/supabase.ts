import { createClient } from '@supabase/supabase-js';

const metaEnv = (import.meta as any).env || {};
const supabaseUrl = metaEnv.VITE_SUPABASE_URL || 'https://placeholder-project.supabase.co';
const supabaseAnonKey = metaEnv.VITE_SUPABASE_ANON_KEY || 'placeholder-anon-key';

// Initialize Supabase Client
// Note: Service role keys are STRICTLY prohibited on the frontend per security architecture!
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
