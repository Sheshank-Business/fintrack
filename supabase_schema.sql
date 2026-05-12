-- Fintrack Supabase schema
-- Run once in Supabase SQL Editor

create extension if not exists pgcrypto;

create table if not exists transactions (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  date date not null,
  type text not null,
  category text not null,
  amount numeric not null,
  payment_method text default 'Cash',
  note text default '',
  created_at timestamp default now()
);

-- If upgrading an existing table, run this:
-- alter table transactions add column if not exists payment_method text default 'Cash';

create table if not exists budgets (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  month text not null,
  amount numeric not null,
  unique(user_id, month)
);

create table if not exists category_limits (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  category text not null,
  amount numeric not null,
  unique(user_id, category)
);

create table if not exists configs (
  id uuid default gen_random_uuid() primary key,
  key text not null unique,
  value text not null default ''
);
