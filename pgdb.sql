-- OPTION 1: PostgreSQL with JSONB (RECOMMENDED)
-- Best balance of SQL reliability with flexible JSON storage

-- Players and Characters
CREATE TABLE players (
    player_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferences JSONB DEFAULT '{}'
);

CREATE TABLE characters (
    character_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID REFERENCES players(player_id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    backstory JSONB DEFAULT '{}',
    traits TEXT[],
    goals TEXT[],
    relationships JSONB DEFAULT '{}',
    stats JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Campaigns and Sessions
CREATE TABLE campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    dm_player_id UUID REFERENCES players(player_id),
    world_state JSONB DEFAULT '{}',
    current_scene TEXT,
    active_npcs JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    session_number INTEGER NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    summary TEXT,
    world_changes JSONB DEFAULT '[]'
);

-- Dialog and Actions (Core game flow)
CREATE TABLE dialog_history (
    dialog_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    speaker_type VARCHAR(20) NOT NULL, -- 'player', 'dm', 'npc', 'system'
    speaker_id UUID, -- player_id or npc_id
    character_name VARCHAR(100),
    content TEXT NOT NULL,
    dialog_type VARCHAR(20) DEFAULT 'narration',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Player Actions and Choices
CREATE TABLE player_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(player_id),
    character_id UUID REFERENCES characters(character_id),
    action_description TEXT NOT NULL,
    action_type VARCHAR(20), -- 'social', 'tactical', 'narrative', 'creative', 'combat'
    intended_outcome TEXT,
    is_creative BOOLEAN DEFAULT FALSE,
    roll_result INTEGER,
    success_level VARCHAR(20), -- 'success', 'failure', 'complication', 'mixed'
    consequences JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Choice tracking for the 7 invisible forces
CREATE TABLE unpaid_consequences (
    consequence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(session_id),
    character_id UUID REFERENCES characters(character_id),
    choice_description TEXT NOT NULL,
    consequence_type VARCHAR(20), -- 'personal', 'local', 'ripple'
    resolved BOOLEAN DEFAULT FALSE,
    resolution_session_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Character development tracking
CREATE TABLE character_threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID REFERENCES characters(character_id) ON DELETE CASCADE,
    thread_type VARCHAR(20), -- 'backstory', 'goal', 'relationship', 'trait'
    description TEXT NOT NULL,
    last_referenced_session UUID REFERENCES sessions(session_id),
    importance_level INTEGER DEFAULT 1, -- 1-5 scale
    resolved BOOLEAN DEFAULT FALSE,
    notes JSONB DEFAULT '{}'
);

-- World state changes (for lasting consequences)
CREATE TABLE world_changes (
    change_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(session_id),
    change_type VARCHAR(50), -- 'location', 'npc', 'faction', 'event', 'reputation'
    entity_name VARCHAR(200), -- what was changed
    change_description TEXT NOT NULL,
    impact_level VARCHAR(20) DEFAULT 'local', -- 'personal', 'local', 'regional', 'global'
    caused_by_action_id UUID REFERENCES player_actions(action_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_data JSONB DEFAULT '{}'
);

-- NPCs and their relationships
CREATE TABLE npcs (
    npc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    personality JSONB DEFAULT '{}',
    relationships JSONB DEFAULT '{}', -- relationships with characters
    location VARCHAR(200),
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'deceased', 'missing', 'retired'
    importance_level INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_interaction_session UUID REFERENCES sessions(session_id)
);

-- Indexes for performance
CREATE INDEX idx_dialog_session_timestamp ON dialog_history(session_id, timestamp);
CREATE INDEX idx_player_actions_session ON player_actions(session_id);
CREATE INDEX idx_character_threads_character ON character_threads(character_id);
CREATE INDEX idx_unpaid_consequences_campaign ON unpaid_consequences(campaign_id, resolved);
CREATE INDEX idx_world_changes_campaign ON world_changes(campaign_id);
CREATE INDEX idx_characters_campaign ON characters(campaign_id);

-- Example queries for the 7 invisible forces:

-- 1. Get unresolved character threads for recognition opportunities
-- SELECT * FROM character_threads 
-- WHERE character_id = $1 AND resolved = FALSE 
-- ORDER BY importance_level DESC, last_referenced_session ASC NULLS FIRST;

-- 2. Get unpaid consequences for future plot development
-- SELECT * FROM unpaid_consequences 
-- WHERE campaign_id = $1 AND resolved = FALSE 
-- ORDER BY created_at ASC;

-- 3. Track how player choices changed the world
-- SELECT wc.*, pa.action_description 
-- FROM world_changes wc 
-- JOIN player_actions pa ON wc.caused_by_action_id = pa.action_id 
-- WHERE wc.campaign_id = $1 ORDER BY wc.created_at DESC;

-- 4. Get recent dialog for context-aware responses
-- SELECT * FROM dialog_history 
-- WHERE session_id = $1 
-- ORDER BY timestamp DESC LIMIT 20;