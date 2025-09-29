# Data Model

## Entities

### Run

- site_id: str
- year: int
- start_ts_utc: datetime
- end_ts_utc: datetime
- duration_s: float
- storage_tag: str | None
- profile_enabled: bool
- outputs: list[Path]

### Scenario

- scenario_id: str
- settings: dict[str, Any]
- output_dir: Path

### ProvenanceRecord

- command: str
- args: dict
- config_digest: str
- hash_alg: str
- inputs: list[{ path: str, size: int, checksum: str }]
- env: { os: str, python: str, eddypro: str }
- start_ts_utc: str
- end_ts_utc: str
- duration_s: float
- storage_tag: str | None
- scenario_settings: dict | None

### PerformanceSnapshot

- ts_utc: str
- cpu_percent: float
- rss_bytes: int
- read_bytes: int
- write_bytes: int
- read_count: int
- write_count: int

### ScenarioIndexRow

- scenario_id: str
- rotation: str
- detrending: str
- qc_preset: str
- n_ok: int
- n_warn: int
- n_err: int
- duration_s: float
- throughput_mb_s: float
