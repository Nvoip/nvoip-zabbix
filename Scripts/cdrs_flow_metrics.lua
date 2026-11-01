-- NN-6660: read-only aggregate sensor for the CronJobs host.
-- Run as root with the existing Aurora connection; publish stdout atomically.

local ok = pcall(dofile, "/etc/nvoip/database-configuration/db-att.lua")
if not ok or type(openAurora1) ~= "function" then
  io.stderr:write("cdrs_flow_metrics: database connection unavailable\n")
  os.exit(1)
end

local connected = pcall(openAurora1)
if not connected or not con then
  io.stderr:write("cdrs_flow_metrics: database connection failed\n")
  os.exit(1)
end

local function run(sql)
  local result = con:execute(sql)
  if not result then error("read-only query failed") end
  return result
end

local query = [[
SELECT COUNT(*) AS total,
       COALESCE(TIMESTAMPDIFF(SECOND, MIN(created_at), NOW()), 0) AS oldest_age_seconds,
       COALESCE(SUM(created_at <= NOW() - INTERVAL 24 HOUR), 0) AS overdue_24h,
       COALESCE(SUM(created_at >= NOW() - INTERVAL 5 MINUTE), 0) AS created_5m
  FROM astpp.cdrs_flow
]]

local success, row = pcall(function()
  run("SET SESSION TRANSACTION READ ONLY")
  run("SET SESSION max_execution_time=3000")
  local cursor = run(query)
  local value = cursor:fetch({}, "a")
  cursor:close()
  if not value then error("aggregate row missing") end
  return value
end)

if type(closeAurora1) == "function" then pcall(closeAurora1) end
if not success then
  io.stderr:write("cdrs_flow_metrics: aggregate query failed\n")
  os.exit(1)
end

for _, field in ipairs({"total", "oldest_age_seconds", "overdue_24h", "created_5m"}) do
  local number = tonumber(row[field])
  if not number or number < 0 then
    io.stderr:write("cdrs_flow_metrics: invalid aggregate\n")
    os.exit(1)
  end
  print(field .. "=" .. math.floor(number))
end
print("updated_epoch=" .. os.time())
