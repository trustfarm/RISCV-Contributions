## Base AME - for Scaled Activator / Scaled Weight

```
A Tile (FP8) ───┐
                ├──► × SA (Scaled Activator)
                │
B Tile (FP8) ───┤
                ├──► × SW (Scaled Weight)
                │
                ▼
     [ Dequant + Multiply-Accumulate Pipeline ]
                │
                ▼
          Accumulator (C, FP32)
                │
                ├─► Astore → External Memory (bTOP=1)
                └─► Internal A-RF (bTOP=0)

```

## VNS Extended X-AME Fine-Grain Scaling Pipeline


```
            ┌────────────────────────────────────────────────────────────┐
            │                    SCALE PATH (Sideband)                   │
            │ *peek/commit hides latency; 1 Tile / 1 Clock maintained.*  │
            │ ┌─────────┐  ┌─────────────┐           ┌────────────┐      │
            │ │ SA_next │─>│ SA_prefetch │─partial─> │ SA_current │──────┼──┐
CSR/DMA ──> │ │ SW_next │─>│ SW_prefetch │─peek   ─> │ SW_current │──────┼──┼──┐ 
            │ └─────────┘  └─────────────┘           └────────────┘      │  │  │
            │       ▲ commit          km progress, trigger     ▲         │  │  │
            │       │                      feedback ───────────┘         │  │  │
            └───────┼────────────────────────────────────────────────────┘  │  │ 
                    │                                                       │  │ 
                    ▼                                                       │  │ 
A Tile (FP8) ────────────────┐<─────────────────────────────────────────────┘  │
                             │                                                 │
                             ├───────> (FP8→FP16 Dequant)                      │ 
                             │       × SA_current(Scaled Activator)            │
                             │                                                 │
                             │                                                 │
                             │<────────────────────────────────────────────────┘
B Tile (FP8) ────────────────┤                                                          
                             ├───────> (FP8→FP16 Dequant)                
                             │         × SW_current (Scaled Weight) 
                             │                                                     
                             ▼
            ┌──────────────────────────────────────────────────────┐
            │   [ Dequant + Multiply-Accumulate Pipeline ]         │
            │   – A×B using current SA/SW scales                   │
            │   – 1 Tile / 1 Clock throughput maintained           │
            │   – Feedback: update km_progress, peek_next scales   │
            └──────────────────────────────────────────────────────┘
                             │
                             ▼
            ┌──────────────────────────────┐
            │  Accumulator (C, FP32)       │
            │  • Internal A-RF (bTOP=0)    │
            │  • External DMA path (bTOP=1)│
            └──────────────────────────────┘
                             │
                             ├─► Astore (bTOP=1) → External Memory 
                             │    
                             └─► Internal Acc (bTOP=0)
                                 Local A-RF Tile Bank 

```
