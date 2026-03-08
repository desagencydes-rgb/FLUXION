-- FLUXION SaaS - PostgreSQL Schema (Multi-Tenant)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum for User Roles
CREATE TYPE user_role AS ENUM ('super_admin', 'fleet_manager', 'driver');
-- Enum for Point Types
CREATE TYPE point_type AS ENUM ('waste_basket', 'recycling', 'fuel', 'restaurant', 'pharmacy', 'hotel', 'supermarket', 'depot');

-----------------------------------------------------------
-- 1. Organizations (Tenants)
-----------------------------------------------------------
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-----------------------------------------------------------
-- 2. Users (RBAC)
-----------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'driver',
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-----------------------------------------------------------
-- 3. Camions (Fleet)
-----------------------------------------------------------
CREATE TABLE camions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plate_number VARCHAR(50) NOT NULL,
    capacite DECIMAL(10, 2) NOT NULL, -- Capacity in kg or volume
    cout_fixe DECIMAL(10, 2) NOT NULL, -- Fixed daily operational cost
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-----------------------------------------------------------
-- 4. Points de Collecte (Network Nodes)
-----------------------------------------------------------
CREATE TABLE points_collecte (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    external_id VARCHAR(100), -- E.g., OSM ID or Geoapify Place ID
    nom VARCHAR(255) NOT NULL,
    type point_type NOT NULL,
    
    -- Original mapped coordinates
    lat DECIMAL(10, 7) NOT NULL,
    lon DECIMAL(10, 7) NOT NULL,
    
    -- Manual Overrides (as requested in Manifest)
    override_lat DECIMAL(10, 7),
    override_lon DECIMAL(10, 7),
    
    -- Properties
    volume_estime DECIMAL(10, 2) DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for spatial bounding box queries (PostGIS geography could be used here)
CREATE INDEX idx_points_org ON points_collecte(organization_id);

-----------------------------------------------------------
-- 5. Savings Logs (ROI Tracking)
-----------------------------------------------------------
CREATE TABLE savings_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Naive vs Optimized comparison
    distance_naive_km DECIMAL(10, 2) NOT NULL,
    distance_optimized_km DECIMAL(10, 2) NOT NULL,
    
    -- Computed Savings
    distance_saved_km DECIMAL(10, 2) GENERATED ALWAYS AS (distance_naive_km - distance_optimized_km) STORED,
    money_saved DECIMAL(10, 2) NOT NULL,
    co2_reduced_kg DECIMAL(10, 2) NOT NULL,
    fuel_saved_l DECIMAL(10, 2) NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_savings_org_date ON savings_logs(organization_id, log_date);
