-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    permissions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Groups table
CREATE TABLE IF NOT EXISTS groups (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    storage_quota BIGINT DEFAULT 0,
    max_users INTEGER DEFAULT 0,
    admin_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_by UUID REFERENCES auth.users(id),
    logo_url TEXT,
    theme_settings JSONB DEFAULT '{}'
);

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT,
    phone_verified BOOLEAN DEFAULT false,
    email TEXT UNIQUE,
    email_verified BOOLEAN DEFAULT false,
    role_id UUID REFERENCES roles(id),
    group_id UUID REFERENCES groups(id),
    status TEXT DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    avatar_url TEXT,
    last_password_change TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_login TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    storage_used BIGINT DEFAULT 0,
    preferred_language TEXT DEFAULT 'fr',
    theme_preference TEXT DEFAULT 'light',
    two_factor_enabled BOOLEAN DEFAULT false,
    two_factor_method TEXT,
    backup_codes TEXT[],
    security_questions JSONB DEFAULT '{}',
    last_security_update TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- OTP codes table
CREATE TABLE IF NOT EXISTS otp_codes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    phone_number TEXT,
    code TEXT NOT NULL,
    type TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    attempts INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    ip_address INET
);

-- Password reset history table
CREATE TABLE IF NOT EXISTS password_reset_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'requested',
    ip_address INET,
    user_agent TEXT,
    reset_method TEXT,
    otp_id UUID REFERENCES otp_codes(id)
);

-- Phone verification table
CREATE TABLE IF NOT EXISTS phone_verification (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    phone_number TEXT NOT NULL,
    verified BOOLEAN DEFAULT false,
    verified_at TIMESTAMP WITH TIME ZONE,
    last_verification_attempt TIMESTAMP WITH TIME ZONE,
    verification_attempts INTEGER DEFAULT 0,
    otp_id UUID REFERENCES otp_codes(id)
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    original_name TEXT NOT NULL,
    generated_name TEXT NOT NULL,
    file_type TEXT NOT NULL,  -- PDF ou CSV
    mime_type TEXT,
    google_drive_id TEXT,
    google_drive_url TEXT,
    checksum TEXT,  -- Pour vérifier l'intégrité
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    user_id UUID REFERENCES auth.users(id),
    group_id UUID REFERENCES groups(id),
    processing_time INTERVAL,
    file_size BIGINT,
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, error
    version INTEGER DEFAULT 1,  -- Pour le versioning des fichiers
    tags TEXT[],  -- Pour la catégorisation
    metadata JSONB DEFAULT '{}',  -- Métadonnées additionnelles
    is_favorite BOOLEAN DEFAULT false,
    last_viewed TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,
    shared_with JSONB DEFAULT '{}',  -- Paramètres de partage
    conversion_type TEXT,  -- Type de conversion effectuée
    output_format TEXT,  -- Format de sortie
    error_message TEXT,  -- Message d'erreur si échec
    processing_options JSONB DEFAULT '{}'  -- Options de traitement
);

-- File comments table
CREATE TABLE IF NOT EXISTS file_comments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    file_id UUID REFERENCES files(id),
    user_id UUID REFERENCES auth.users(id),
    comment TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    parent_comment_id UUID REFERENCES file_comments(id),
    mentions UUID[]  -- Utilisateurs mentionnés
);

-- Processing statistics table
CREATE TABLE IF NOT EXISTS processing_stats (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    group_id UUID REFERENCES groups(id),
    file_id UUID REFERENCES files(id),
    processing_start TIMESTAMP WITH TIME ZONE DEFAULT now(),
    processing_end TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL,  -- success, error
    error_message TEXT,
    processing_details JSONB DEFAULT '{}',  -- Détails techniques
    resource_usage JSONB DEFAULT '{}',  -- CPU, mémoire, etc.
    conversion_type TEXT NOT NULL,  -- Type de conversion
    input_format TEXT NOT NULL,
    output_format TEXT NOT NULL,
    input_size BIGINT,  -- Taille du fichier d'entrée
    output_size BIGINT,  -- Taille du fichier de sortie
    processing_duration INTERVAL,  -- Durée de traitement
    success_rate NUMERIC,  -- Taux de réussite (0-100)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Usage metrics table for dashboard
CREATE TABLE IF NOT EXISTS usage_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    group_id UUID REFERENCES groups(id),
    metric_type TEXT NOT NULL,  -- daily, weekly, monthly
    date DATE NOT NULL,
    files_processed INTEGER DEFAULT 0,
    total_size BIGINT DEFAULT 0,
    average_processing_time INTERVAL,
    success_rate NUMERIC DEFAULT 0,  -- Taux de réussite global
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    peak_usage_time TIME,  -- Heure de pic d'utilisation
    cost_estimate NUMERIC DEFAULT 0,  -- Estimation des coûts
    conversion_types_count JSONB DEFAULT '{}',  -- Comptage par type de conversion
    error_count INTEGER DEFAULT 0,  -- Nombre d'erreurs
    active_users_count INTEGER DEFAULT 0,  -- Nombre d'utilisateurs actifs
    storage_used BIGINT DEFAULT 0,  -- Stockage total utilisé
    bandwidth_used BIGINT DEFAULT 0,  -- Bande passante utilisée
    popular_file_types JSONB DEFAULT '{}',  -- Types de fichiers les plus populaires
    performance_metrics JSONB DEFAULT '{}'  -- Métriques de performance
);

-- Insert default roles
INSERT INTO roles (name, description, permissions) VALUES
('superadmin', 'Super administrateur avec accès complet', '{
    "users": ["create", "read", "update", "delete"],
    "groups": ["create", "read", "update", "delete"],
    "files": ["create", "read", "update", "delete"],
    "stats": ["read"],
    "system": ["configure"]
}'),
('admin', 'Administrateur de groupe', '{
    "users": ["create", "read", "update"],
    "groups": ["read"],
    "files": ["read", "delete"],
    "stats": ["read"]
}'),
('user', 'Utilisateur standard', '{
    "files": ["create", "read"],
    "stats": ["read_own"]
}')
ON CONFLICT (name) DO NOTHING;

-- Create RLS policies
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE otp_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_verification ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_metrics ENABLE ROW LEVEL SECURITY;

-- Policies for roles
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'roles' 
        AND policyname = 'Roles visibles par tous les utilisateurs authentifiés'
    ) THEN
        CREATE POLICY "Roles visibles par tous les utilisateurs authentifiés" ON roles
            FOR SELECT
            TO authenticated
            USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'roles' 
        AND policyname = 'Seul le superadmin peut modifier les rôles'
    ) THEN
        CREATE POLICY "Seul le superadmin peut modifier les rôles" ON roles
            FOR ALL
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM user_profiles up
                    WHERE up.id = auth.uid()
                    AND EXISTS (
                        SELECT 1 FROM roles r
                        WHERE r.id = up.role_id
                        AND r.name = 'superadmin'
                    )
                )
            );
    END IF;
END $$;

-- Policies for groups
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'groups' 
        AND policyname = 'Groupes visibles par les membres'
    ) THEN
        CREATE POLICY "Groupes visibles par les membres" ON groups
            FOR SELECT
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM user_profiles up
                    WHERE up.id = auth.uid()
                    AND (up.group_id = groups.id OR groups.admin_id = auth.uid())
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'groups' 
        AND policyname = 'Seul l''admin du groupe peut modifier'
    ) THEN
        CREATE POLICY "Seul l'admin du groupe peut modifier" ON groups
            FOR ALL
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM user_profiles up
                    WHERE up.id = auth.uid()
                    AND (
                        groups.admin_id = auth.uid()
                        OR EXISTS (
                            SELECT 1 FROM roles r
                            WHERE r.id = up.role_id
                            AND r.name = 'superadmin'
                        )
                    )
                )
            );
    END IF;
END $$;

-- Policies for user_profiles
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'user_profiles' 
        AND policyname = 'Utilisateurs visibles par les membres du même groupe'
    ) THEN
        CREATE POLICY "Utilisateurs visibles par les membres du même groupe" ON user_profiles
            FOR SELECT
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM user_profiles up
                    WHERE up.id = auth.uid()
                    AND (
                        up.group_id = user_profiles.group_id
                        OR EXISTS (
                            SELECT 1 FROM roles r
                            WHERE r.id = up.role_id
                            AND r.name IN ('admin', 'superadmin')
                        )
                    )
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'user_profiles' 
        AND policyname = 'Utilisateurs peuvent modifier leur propre profil'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent modifier leur propre profil" ON user_profiles
            FOR UPDATE
            TO authenticated
            USING (id = auth.uid());
    END IF;
END $$;

-- Policies for OTP codes
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'otp_codes' 
        AND policyname = 'OTP visibles uniquement par l''utilisateur concerné'
    ) THEN
        CREATE POLICY "OTP visibles uniquement par l'utilisateur concerné" ON otp_codes
            FOR ALL
            TO authenticated
            USING (user_id = auth.uid());
    END IF;
END $$;

-- Policies for password reset history
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'password_reset_history' 
        AND policyname = 'Historique de réinitialisation visible uniquement par l''utilisateur'
    ) THEN
        CREATE POLICY "Historique de réinitialisation visible uniquement par l'utilisateur" ON password_reset_history
            FOR ALL
            TO authenticated
            USING (user_id = auth.uid());
    END IF;
END $$;

-- Policies for phone verification
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'phone_verification' 
        AND policyname = 'Vérification de téléphone visible uniquement par l''utilisateur'
    ) THEN
        CREATE POLICY "Vérification de téléphone visible uniquement par l'utilisateur" ON phone_verification
            FOR ALL
            TO authenticated
            USING (user_id = auth.uid());
    END IF;
END $$;

-- Policies for files
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'files' 
        AND policyname = 'Utilisateurs peuvent voir leurs propres fichiers'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent voir leurs propres fichiers" ON files
            FOR SELECT
            TO authenticated
            USING (
                user_id = auth.uid()
                OR EXISTS (
                    SELECT 1 FROM user_profiles up
                    WHERE up.id = auth.uid()
                    AND up.group_id = files.group_id
                    AND EXISTS (
                        SELECT 1 FROM roles r
                        WHERE r.id = up.role_id
                        AND (r.name = 'admin' OR r.name = 'superadmin')
                    )
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'files' 
        AND policyname = 'Utilisateurs peuvent créer des fichiers'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent créer des fichiers" ON files
            FOR INSERT
            TO authenticated
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'files' 
        AND policyname = 'Utilisateurs peuvent modifier leurs propres fichiers'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent modifier leurs propres fichiers" ON files
            FOR UPDATE
            TO authenticated
            USING (user_id = auth.uid());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'files' 
        AND policyname = 'Utilisateurs peuvent supprimer leurs propres fichiers'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent supprimer leurs propres fichiers" ON files
            FOR DELETE
            TO authenticated
            USING (user_id = auth.uid());
    END IF;
END $$;

-- Policies for file comments
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'file_comments' 
        AND policyname = 'Tout le monde peut voir les commentaires'
    ) THEN
        CREATE POLICY "Tout le monde peut voir les commentaires" ON file_comments
            FOR SELECT
            TO authenticated
            USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'file_comments' 
        AND policyname = 'Utilisateurs peuvent créer des commentaires'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent créer des commentaires" ON file_comments
            FOR INSERT
            TO authenticated
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'file_comments' 
        AND policyname = 'Utilisateurs peuvent modifier leurs propres commentaires'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent modifier leurs propres commentaires" ON file_comments
            FOR UPDATE
            TO authenticated
            USING (user_id = auth.uid());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'file_comments' 
        AND policyname = 'Utilisateurs peuvent supprimer leurs propres commentaires'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent supprimer leurs propres commentaires" ON file_comments
            FOR DELETE
            TO authenticated
            USING (user_id = auth.uid());
    END IF;
END $$;

-- Policies for processing stats
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'processing_stats' 
        AND policyname = 'Utilisateurs peuvent voir leurs propres statistiques'
    ) THEN
        CREATE POLICY "Utilisateurs peuvent voir leurs propres statistiques" ON processing_stats
            FOR SELECT
            TO authenticated
            USING (
                user_id = auth.uid()
                OR EXISTS (
                    SELECT 1 FROM user_profiles up
                    WHERE up.id = auth.uid()
                    AND up.group_id = processing_stats.group_id
                    AND EXISTS (
                        SELECT 1 FROM roles r
                        WHERE r.id = up.role_id
                        AND (r.name = 'admin' OR r.name = 'superadmin')
                    )
                )
            );
    END IF;
END $$;

-- Policies for usage metrics
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'usage_metrics' 
        AND policyname = 'Administrateurs peuvent voir les métriques'
    ) THEN
        CREATE POLICY "Administrateurs peuvent voir les métriques" ON usage_metrics
            FOR SELECT
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM user_profiles up
                    WHERE up.id = auth.uid()
                    AND (
                        up.group_id = usage_metrics.group_id
                        OR EXISTS (
                            SELECT 1 FROM roles r
                            WHERE r.id = up.role_id
                            AND r.name = 'superadmin'
                        )
                    )
                )
            );
    END IF;
END $$;

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_group_id ON files(group_id);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);

CREATE INDEX IF NOT EXISTS idx_processing_stats_user_id ON processing_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_processing_stats_group_id ON processing_stats(group_id);
CREATE INDEX IF NOT EXISTS idx_processing_stats_created_at ON processing_stats(created_at);

CREATE INDEX IF NOT EXISTS idx_usage_metrics_date ON usage_metrics(date);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_group_id ON usage_metrics(group_id);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_metric_type ON usage_metrics(metric_type);
