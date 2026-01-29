-- Run this SQL in your Supabase SQL Editor to create the interactions table

create table if not exists interactions (
  id bigint primary key generated always as identity,
  timestamp timeout with time zone default now(),
  query text not null,
  success boolean not null,
  
  -- Full LLM outputs (JSON logs)
  expander_output jsonb,
  decomposer_output jsonb,
  generator_output jsonb,
  formatter_output jsonb,
  
  -- Final Results
  final_result_json jsonb,
  error_message text,
  response_summary text
);

-- Optional: Enable Row Level Security (RLS) if you want to restrict access
-- alter table interactions enable row level security;
-- create policy "Enable read access for all users" on interactions for select using (true);
-- create policy "Enable insert access for all users" on interactions for insert with check (true);
