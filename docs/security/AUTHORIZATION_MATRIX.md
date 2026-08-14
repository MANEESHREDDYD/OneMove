# ZonePilot Security Authorization Matrix

| Resource / Action | OWNER Role | OBSERVER Role | VOLUNTEER Role | Anonymous / Public |
| :--- | :--- | :--- | :--- | :--- |
| **Read Study Metadata** | `ALLOW` | `ALLOW` (Assigned) | `ALLOW` (Assigned) | `DENY` |
| **Create Probe Observation** | `DENY` | `ALLOW` (Active Assignment) | `DENY` | `DENY` |
| **Read Probe Observations** | `ALLOW` (Study Scoped) | `ALLOW` (Own Probes) | `DENY` | `DENY` |
| **Read Current Probes View** | `ALLOW` (Study Scoped) | `ALLOW` (Own Probes via RLS) | `DENY` | `DENY` |
| **Create Volunteer Order Event** | `DENY` | `DENY` | `ALLOW` (Own Orders) | `DENY` |
| **Modify User Roles** | `ALLOW` | `DENY` | `DENY` | `DENY` |
| **Bypass RLS via API** | `DENY` | `DENY` | `DENY` | `DENY` |
| **Read Private Raw Parquet** | `ALLOW` (Local Disk) | `DENY` | `DENY` | `DENY` |
