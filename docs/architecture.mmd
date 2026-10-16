flowchart TD
    A[Citizen input<br/>photo + complaint + location] -->|text + image + coordinates| B[ML/DL Layer]
    B -->|VLM / vision analysis| C[Vision Model]
    B -->|NLP classification| D[NLP Classifier]
    C -->|visual evidence| E[Fusion Layer]
    D -->|language + category + confidence| E
    E -->|structured incident facts| F[Central Orchestrator]

    F -->|route complaint| G[Agent 1: Incident Intelligence<br/>Tool: VLM + NLP + evidence extraction]
    G -->|needs clarification| H{Needs clarification?}
    H -->|Yes| I[Clarification loop]
    H -->|No| J[Agent 2: Geo-Spatial Intelligence<br/>Tool: haversine + TF-IDF + DBSCAN]
    J -->|duplicate evidence| K{Candidate duplicate?}
    K -->|Yes| L[Duplicate review / UNCONFIRMED]
    K -->|No| M[Agent 3: Risk & Priority<br/>Tool: weighted score + escalation policy]

    M -->|priority band + risk explanation| N[Agent 4: Response Planning<br/>Tool: plan generator + policy config]
    N -->|temp relief + permanent repair plan| O[Execution Simulator<br/>Tool: seeded scenario runner]
    O -->|plan failed| P[Agent 5: Adaptive Recovery<br/>Tool: constraint-based alternative selector]
    P -->|replan| N
    P -->|retry exhausted| Q{Human review?}

    N -->|approved plan + evidence| R[Agent 6: Independent Verification<br/>Tool: evidence checklist + closure validation]
    R -->|verification rejected| S{Reopen or replan?}
    S -->|reopen| I
    S -->|replan| N
    R -->|approved| T[Civic Incident Twin (SQLite)]
    O -->|execution record| T
    T -->|audit timeline + status| U[Dashboard / audit report]

    R -->|escalation required| Q
    Q -->|Yes| V[Human Review]
    Q -->|No| W[Return to orchestrator]

    F -->|state write| T
    T -->|history| U
    O -->|simulated execution result| R

    classDef decision fill:#fff2cc,stroke:#d6b656,stroke-width:1px;
    class H,K,Q,S decision;
