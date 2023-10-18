SELECT 'CREATE DATABASE paste_server' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'paste_server')\gexec

\c paste_server

CREATE TABLE IF NOT EXISTS Users (
  Username TEXT,
  Password TEXT,
  Email TEXT,
  id BIGSERIAL,
  InsecureToken TEXT,
  SecureToken TEXT,
  AvatarType INT, -- 0: Default, 1: Gravatar (from email), 2: URL.
  -- Users can also upload a URL, which will be hosted under /avatars/{id}, which will set avatartype to 2 and set the appropriate URL
  AvatarURL TEXT, -- If avatartype is 2, then this will have a URL.
  RememberMe BOOLEAN -- Last known state of user's rememberme, used for token stuff in non login endpoints
);

CREATE TABLE IF NOT EXISTS Pastes (
  id TEXT,
  Creator BIGINT,
  Content BYTEA,
  Visibility INT,
  Title TEXT,
  Created BIGINT,
  Modified BIGINT,
  Syntax TEXT,
  Tags TEXT
);

CREATE TABLE IF NOT EXISTS APITokens (
  Creator BIGINT,
  Title TEXT,
  Perms INT,
  id TEXT,
  ident TEXT
);

CREATE TABLE IF NOT EXISTS AvatarCache (
  UserID BIGINT UNIQUE,
  Avatar BYTEA,
  Refresh BIGINT
);

CREATE TABLE IF NOT EXISTS Avatars (
  ID BIGINT UNIQUE,
  Avatar BYTEA
);