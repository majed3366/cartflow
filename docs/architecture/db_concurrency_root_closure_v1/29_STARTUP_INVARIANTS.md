# INV-START — Startup / non-request DB ownership

| ID | Invariant |
|----|-----------|
| INV-START-01 | Every startup/lifespan DB session has an explicit non-request owner. |
| INV-START-02 | Startup DB work has a bounded unit-of-work lifetime. |
| INV-START-03 | Completed startup work leaves no checked-out connection. |
| INV-START-04 | Completed startup work leaves no open transaction / idle-in-transaction backend. |
| INV-START-05 | Thread-scope fallback must not become a persistent Session after the startup phase ends. |
| INV-START-06 | Persistent background owners must not hold a DB connection while idle. |
