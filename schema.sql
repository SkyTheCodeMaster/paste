SELECT 'CREATE DATABASE paste_server' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'paste_server')\gexec

\c paste_server

CREATE TABLE IF NOT EXISTS Users (
  Username TEXT,
  Password TEXT,
  Email TEXT,
  id BIGSERIAL,
  Token TEXT
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
  id TEXT
);