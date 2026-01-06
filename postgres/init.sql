-- Dating Bot Platform - Database Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_until TIMESTAMP,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);

CREATE TABLE IF NOT EXISTS vk_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    vk_user_id VARCHAR(50),
    vk_app_id VARCHAR(50) NOT NULL,
    session_data_encrypted BYTEA,
    status VARCHAR(20) DEFAULT 'inactive',
    last_active_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vk_accounts_client ON vk_accounts(client_id);
CREATE INDEX IF NOT EXISTS idx_vk_accounts_status ON vk_accounts(status);

CREATE TABLE IF NOT EXISTS bot_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vk_account_id UUID REFERENCES vk_accounts(id) ON DELETE CASCADE,
    active_quest VARCHAR(50) DEFAULT 'ideal_date',
    quest_filters JSONB DEFAULT '{}',
    boost_times VARCHAR[] DEFAULT ARRAY['19:00', '21:00', '23:00'],
    boost_timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    swipe_interval_minutes INT DEFAULT 30,
    max_swipes_per_session INT DEFAULT 50,
    dialogue_style VARCHAR(20) DEFAULT 'balanced',
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bot_configs_account ON bot_configs(vk_account_id);
CREATE INDEX IF NOT EXISTS idx_bot_configs_active ON bot_configs(is_active) WHERE is_active = true;

CREATE TABLE IF NOT EXISTS activity_log (
    id BIGSERIAL PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    vk_account_id UUID REFERENCES vk_accounts(id),
    action_type VARCHAR(50) NOT NULL,
    target_profile JSONB,
    result VARCHAR(20),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_activity_log_created ON activity_log(created_at);
CREATE INDEX IF NOT EXISTS idx_activity_log_client ON activity_log(client_id);

CREATE TABLE IF NOT EXISTS dialogues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id),
    vk_account_id UUID REFERENCES vk_accounts(id),
    target_profile JSONB NOT NULL,
    target_type VARCHAR(50),
    messages JSONB DEFAULT '[]',
    stage VARCHAR(50) DEFAULT 'started',
    outcome VARCHAR(50),
    outcome_score FLOAT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dialogues_client ON dialogues(client_id);
CREATE INDEX IF NOT EXISTS idx_dialogues_outcome ON dialogues(outcome);

CREATE TABLE IF NOT EXISTS dialogue_patterns (
    id BIGSERIAL PRIMARY KEY,
    girl_type VARCHAR(50),
    stage VARCHAR(50),
    her_message_keywords TEXT[],
    our_message TEXT NOT NULL,
    times_used INT DEFAULT 0,
    times_success INT DEFAULT 0,
    success_rate FLOAT GENERATED ALWAYS AS (CASE WHEN times_used > 0 THEN times_success::FLOAT / times_used ELSE 0 END) STORED,
    contributed_by UUID REFERENCES clients(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patterns_lookup ON dialogue_patterns(girl_type, stage, success_rate DESC);

CREATE OR REPLACE FUNCTION update_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_clients_updated_at ON clients;
CREATE TRIGGER trigger_clients_updated_at BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trigger_vk_accounts_updated_at ON vk_accounts;
CREATE TRIGGER trigger_vk_accounts_updated_at BEFORE UPDATE ON vk_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at();

INSERT INTO dialogue_patterns (girl_type, stage, her_message_keywords, our_message) VALUES
('any', 'opener', '{}', 'Привет! Заметил тебя в ленте, интересный профиль'),
('any', 'opener', '{}', 'Привет! Как твой день проходит?'),
('investor', 'opener', ARRAY['бизнес', 'инвестор'], 'Привет! Вижу, ты в сфере инвестиций. Было бы интересно пообщаться!'),
('romantic', 'opener', ARRAY['романтик', 'любовь'], 'Привет! У тебя очень тёплый профиль'),
('any', 'building_rapport', ARRAY['привет', 'hi'], 'Как настроение? Чем занимаешься?')
ON CONFLICT DO NOTHING;

CREATE OR REPLACE VIEW active_bots AS
SELECT va.id as account_id, va.client_id, va.vk_app_id, va.status, va.last_active_at,
       bc.active_quest, bc.quest_filters, bc.boost_times, bc.swipe_interval_minutes
FROM vk_accounts va
JOIN bot_configs bc ON va.id = bc.vk_account_id
WHERE bc.is_active = true;
