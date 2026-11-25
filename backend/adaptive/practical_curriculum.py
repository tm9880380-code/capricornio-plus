"""Currículo práctico modular y generador determinista de retos.

Los retos son especificaciones evaluables, no texto aleatorio: cada uno define
un objetivo, contexto, entregables, criterios de aceptación y nivel. La ejecución
del código del estudiante debe ocurrir en un sandbox aislado del navegador/runner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

AREA_MODULES = {
    "ciberseguridad": [
        ("Linux for Security Operations", "Linux permissions, users, processes and forensic command-line workflows", "Build a read-only triage script that inventories users, permissions, processes and suspicious persistence from supplied fixture data."),
        ("Windows Administration and Hardening", "Windows accounts, services, event logs, PowerShell and baseline hardening", "Write defensive PowerShell-style logic against synthetic Windows host inventories and event records."),
        ("Networking Fundamentals and Packet Analysis", "TCP/IP, subnetting, DNS, DHCP, routing and packet interpretation", "Parse synthetic packet captures and reconstruct network conversations, anomalies and protocol failures."),
        ("Python for Defensive Security", "Python data structures, parsing, automation, testing and robust error handling", "Implement tested Python utilities for security telemetry ingestion, normalization and correlation."),
        ("Identity, Authentication and Access Control", "Authentication flows, MFA, sessions, RBAC, least privilege and access reviews", "Audit synthetic identity records and detect privilege escalation, stale accounts and broken authorization."),
        ("Cryptography and Key Management", "Hashing, signatures, TLS concepts, key lifecycle and cryptographic misuse", "Build safe cryptographic inventory and verification tools using standard-library primitives and supplied fixtures."),
        ("Web Security and OWASP Top 10:2025", "Access control, misconfiguration, supply chain, injection and secure design", "Find and remediate vulnerabilities in intentionally vulnerable local code snippets and test harnesses."),
        ("Secure Software Development and Code Review", "Threat modeling, input validation, secrets, dependencies and secure coding", "Review a deliberately flawed application, implement fixes and prove them with regression tests."),
        ("Vulnerability Management and Risk Prioritization", "Asset inventory, CVE/CVSS context, exposure, remediation and verification", "Prioritize synthetic findings using exploitability, asset criticality and compensating controls."),
        ("SIEM, Logs and Detection Engineering", "Log pipelines, parsing, normalization, correlation rules and alert quality", "Create detection logic over synthetic authentication, endpoint and network event streams."),
        ("Incident Response and Digital Forensics", "Preparation, triage, containment, evidence integrity and timelines", "Reconstruct incidents from provided disk, process and event artifacts while preserving evidence."),
        ("Threat Intelligence and MITRE ATT&CK", "Adversary behavior, ATT&CK mapping, intelligence lifecycle and hypotheses", "Map observed behaviors to ATT&CK techniques and produce evidence-backed detection hypotheses."),
        ("Cloud and Container Security", "Shared responsibility, IAM, storage exposure, container images and runtime controls", "Audit synthetic cloud policies and container configurations, then produce least-privilege remediations."),
        ("Security Architecture, Governance and Risk", "Security controls, policies, third-party risk, resilience and governance", "Design a defensible control plan for a realistic small-enterprise scenario with measurable evidence."),
        ("Capstone: Security Operations and Purple-Team Assessment", "Integrated detection, secure configuration, incident handling and reporting", "Deliver an end-to-end defensive assessment using only isolated lab fixtures, with reproducible tests and an executive report."),
    ],
    "programacion": [
        ("Computational Thinking and Problem Decomposition", "Algorithms, invariants, complexity and precise problem specifications", "Translate ambiguous requirements into tested algorithms and explicit edge-case contracts."),
        ("Python Foundations and Control Flow", "Types, functions, iteration, exceptions and clean interfaces", "Build robust command-line programs from specifications and adversarial test cases."),
        ("Data Structures and Algorithmic Complexity", "Arrays, hash maps, stacks, queues, trees, graphs and Big-O", "Choose data structures from workload constraints and justify complexity trade-offs."),
        ("Object-Oriented Design and SOLID", "Encapsulation, composition, polymorphism and design principles", "Refactor tightly coupled code into testable components with clear responsibilities."),
        ("Functional Programming and Advanced Python", "Pure functions, iterators, generators, decorators and typing", "Build composable pipelines with predictable behavior and strict type contracts."),
        ("Testing, Debugging and Property-Based Thinking", "Unit, integration, regression, boundary and property tests", "Diagnose hidden defects and create tests that expose edge cases and regressions."),
        ("Algorithms: Search, Sorting and Optimization", "Divide and conquer, greedy methods, dynamic programming and analysis", "Implement and compare algorithms under explicit time and memory constraints."),
        ("Concurrency, Parallelism and Async Systems", "Threads, processes, async I/O, synchronization and race conditions", "Design concurrent workloads with bounded resources and deterministic correctness tests."),
        ("APIs, Protocols and Distributed Systems", "HTTP, serialization, retries, idempotency and failure handling", "Build resilient service clients and APIs that tolerate partial failures."),
        ("Databases, Transactions and Data Modeling", "Relational design, SQL, indexes, isolation and migrations", "Model a domain, write optimized queries and preserve invariants under concurrent updates."),
        ("Secure Coding and Software Supply Chain", "Input boundaries, dependency risk, secrets and reproducible builds", "Harden an application and produce evidence for dependency and integrity controls."),
        ("Performance Engineering and Profiling", "Profiling, memory, algorithmic bottlenecks and load behavior", "Find bottlenecks from measured traces and prove performance improvements."),
        ("Architecture and Maintainable Systems", "Layering, domain boundaries, observability and architecture decisions", "Design a modular system with explicit contracts, failure modes and architecture tests."),
        ("Systems Programming and Runtime Internals", "Memory, processes, files, networking and low-level interfaces", "Implement low-level utilities with careful resource ownership and defensive error handling."),
        ("Capstone: Production-Grade Software Delivery", "Requirements, implementation, testing, security, deployment and operations", "Deliver a tested application with CI, observability, threat analysis and maintainable documentation."),
    ],
    "frontend": [
        ("Web Platform, HTML and Accessibility", "Semantic HTML, forms, navigation, accessibility and browser behavior", "Build accessible interfaces from semantic requirements and automated checks."),
        ("CSS Layout and Responsive Design", "Cascade, flexbox, grid, responsive systems and visual consistency", "Reconstruct complex responsive layouts with reusable design tokens."),
        ("JavaScript Language and Browser Runtime", "Scopes, closures, prototypes, modules, events and asynchronous behavior", "Implement browser features with predictable state and robust error handling."),
        ("TypeScript and Large-Scale UI Contracts", "Types, generics, narrowing, interfaces and safe refactoring", "Model complex UI data and eliminate unsafe assumptions through type design."),
        ("Component Architecture and State Management", "Composition, state machines, derived state and lifecycle", "Build a multi-step interface with deterministic state transitions."),
        ("Forms, Validation and User Experience", "Client/server validation, accessibility and error recovery", "Implement resilient workflows with edge-case and usability tests."),
        ("HTTP, APIs and Data Fetching", "HTTP semantics, caching, cancellation and race conditions", "Create a data-heavy interface resilient to latency and partial failures."),
        ("Testing Frontend Applications", "Unit, component, integration and browser automation", "Build a test suite that catches regressions in complex interactions."),
        ("Web Security and OWASP", "XSS, CSRF, CSP, authorization and secure browser storage", "Fix intentionally vulnerable UI flows and verify mitigations."),
        ("Performance and Core Web Vitals", "Rendering, bundles, images, caching and profiling", "Optimize a synthetic slow application with measurable before/after evidence."),
        ("Progressive Web Apps and Offline Behavior", "Service workers, caching, synchronization and resilience", "Implement offline-safe behavior with conflict and stale-data handling."),
        ("Design Systems and Visual Engineering", "Tokens, component APIs, themes and consistency", "Create a reusable component system with visual regression criteria."),
        ("Internationalization and Localization", "Locale data, formatting, directionality and accessible content", "Adapt a complex interface to multiple locales without layout regressions."),
        ("Frontend Architecture and Delivery", "Boundaries, build tooling, CI, observability and release strategy", "Prepare a maintainable frontend for staged delivery and rollback."),
        ("Capstone: Enterprise Web Application", "Accessible, secure, performant and tested product interface", "Ship a complete application slice with automated quality gates."),
    ],
    "backend": [
        ("HTTP, REST and API Design", "Methods, status codes, contracts, pagination and versioning", "Design an API contract and implement correct behavior for edge cases."),
        ("Python Services and Runtime Design", "Application structure, dependency injection and configuration", "Build a maintainable service with explicit boundaries and configuration."),
        ("Relational Data Modeling and SQL", "Normalization, constraints, joins and transactions", "Design and query a transactional schema under realistic workload constraints."),
        ("Authentication and Authorization", "Sessions, tokens, RBAC, password storage and threat boundaries", "Implement secure identity flows and prove access-control invariants."),
        ("Validation, Errors and API Resilience", "Schemas, exception handling, retries and idempotency", "Build robust endpoints that fail safely and predictably."),
        ("Caching, Queues and Background Jobs", "Cache invalidation, queues, workers and delivery guarantees", "Implement a reliable asynchronous workflow with duplicate and failure handling."),
        ("Concurrency and Transaction Isolation", "Locks, races, isolation levels and consistency", "Reproduce and resolve concurrency bugs with repeatable tests."),
        ("Testing and Contract Verification", "Unit, integration, contract and property-based testing", "Build comprehensive tests for service boundaries and failure modes."),
        ("Application Security and OWASP", "Injection, access control, SSRF, secrets and supply chain", "Threat-model and remediate a deliberately flawed API."),
        ("Observability and Production Debugging", "Structured logs, metrics, traces and incident diagnosis", "Diagnose a production-style incident from telemetry and reproduce the defect."),
        ("Distributed Systems and Reliability", "Consistency, timeouts, retries, circuit breakers and sagas", "Design a service workflow that remains correct during partial outages."),
        ("Performance and Database Optimization", "Profiling, query plans, indexes and load testing", "Reduce measured latency without violating correctness constraints."),
        ("Containers, CI/CD and Deployment", "Container hardening, pipelines, configuration and rollback", "Create a reproducible deployment pipeline with quality and security gates."),
        ("Architecture, Domain Design and Evolution", "Bounded contexts, modularity, migration and compatibility", "Evolve a service architecture without breaking existing clients."),
        ("Capstone: Production Backend Platform", "Secure APIs, data integrity, observability and delivery", "Deliver a complete backend slice with repeatable tests and operational runbooks."),
    ],
    "datos": [
        ("Data Literacy and Analytical Problem Framing", "Data quality, questions, metrics and analytical reasoning", "Turn a business question into a reproducible analytical specification."),
        ("Python for Data Workflows", "Python, notebooks, functions and reproducible environments", "Build a tested data-cleaning pipeline with explicit assumptions."),
        ("SQL for Analytical Engineering", "Joins, windows, CTEs and query optimization", "Answer complex analytical questions with validated SQL."),
        ("Data Cleaning and Quality Engineering", "Missingness, duplicates, anomalies and validation rules", "Create a quality framework and quantify data defects."),
        ("Statistics and Probability", "Distributions, uncertainty, sampling and inference", "Analyze a dataset and defend conclusions against statistical pitfalls."),
        ("Exploratory Data Analysis", "Summaries, distributions, outliers and hypothesis generation", "Produce an evidence-based exploratory report with reproducible code."),
        ("Visualization and Data Storytelling", "Chart selection, perception, dashboards and narrative", "Build a decision-ready dashboard with defensible visual encoding."),
        ("Experiment Design and A/B Testing", "Randomization, power, bias and causal interpretation", "Analyze an experiment and detect invalid conclusions."),
        ("Machine Learning Foundations", "Features, leakage, validation and baseline models", "Train and evaluate a baseline model without leakage."),
        ("Advanced Modeling and Evaluation", "Ensembles, calibration, imbalance and error analysis", "Compare models under realistic business costs and constraints."),
        ("Time Series and Forecasting", "Temporal validation, seasonality and drift", "Build a forecasting workflow with honest backtesting."),
        ("Data Pipelines and Orchestration", "ETL/ELT, lineage, scheduling and idempotency", "Design a reliable pipeline with recovery and data contracts."),
        ("Big Data and Distributed Processing", "Partitioning, parallelism and distributed computation", "Optimize a distributed transformation under resource limits."),
        ("Governance, Privacy and Responsible Analytics", "Lineage, access, minimization and fairness", "Audit a data product for privacy, quality and decision risk."),
        ("Capstone: End-to-End Analytics Product", "Ingestion, modeling, evaluation and communication", "Deliver a reproducible analytical product with a stakeholder report."),
    ],
    "bases-datos": [
        ("Database Concepts and Relational Modeling", "Entities, relationships, keys and constraints", "Model a complex domain with normalized relational structures."),
        ("SQL Foundations and Query Semantics", "Filtering, joins, grouping and NULL semantics", "Write precise queries for adversarial data fixtures."),
        ("Advanced SQL and Window Functions", "CTEs, windows, recursive queries and set operations", "Solve analytical query challenges with correctness and efficiency."),
        ("Normalization and Schema Design", "Functional dependencies and normal forms", "Refactor a flawed schema and justify trade-offs."),
        ("Transactions and ACID", "Atomicity, consistency, isolation and durability", "Reproduce anomalies and enforce transaction invariants."),
        ("Indexes and Query Planning", "B-trees, selectivity, plans and statistics", "Optimize slow queries using measured execution plans."),
        ("Database Security and Access Control", "Roles, grants, encryption and auditing", "Design least-privilege access and test prohibited operations."),
        ("Backup, Recovery and Continuity", "Backup strategies, point-in-time recovery and RPO/RTO", "Prove a recovery plan against simulated failure scenarios."),
        ("NoSQL and Data Modeling Alternatives", "Document, key-value, graph and consistency models", "Select and model a non-relational store for explicit access patterns."),
        ("Replication and High Availability", "Replication lag, failover and consistency", "Analyze failover behavior and prevent stale-read assumptions."),
        ("Performance and Workload Engineering", "Concurrency, connection pools and workload patterns", "Diagnose contention and improve throughput without data loss."),
        ("Data Warehousing and Dimensional Modeling", "Facts, dimensions, star schemas and slowly changing dimensions", "Build a dimensional model and validate business metrics."),
        ("Migrations and Schema Evolution", "Versioning, expand-contract and rollback", "Deploy a backward-compatible migration under concurrent traffic."),
        ("Observability and Database Operations", "Metrics, logs, locks and incident response", "Diagnose a database incident from synthetic operational telemetry."),
        ("Capstone: Reliable Data Platform", "Modeling, security, operations and analytics", "Deliver a secure and recoverable database platform design and implementation."),
    ],
    "ia": [
        ("Mathematics and Foundations for Machine Learning", "Linear algebra, probability, optimization and loss functions", "Implement and test core numerical routines on bounded datasets."),
        ("Python and Data Preparation for ML", "Pipelines, features, validation and reproducibility", "Build a leakage-resistant preprocessing pipeline."),
        ("Supervised Learning", "Regression, classification and baseline evaluation", "Compare supervised models using defensible validation."),
        ("Unsupervised Learning", "Clustering, dimensionality reduction and anomaly detection", "Evaluate clusters and anomalies without overstating labels."),
        ("Model Evaluation and Statistical Validation", "Cross-validation, calibration, metrics and uncertainty", "Select metrics aligned with operational costs."),
        ("Neural Networks and Deep Learning", "Backpropagation, architectures and regularization", "Implement and diagnose a compact neural model."),
        ("Natural Language Processing", "Tokenization, embeddings, sequence and evaluation", "Build an NLP pipeline with error analysis."),
        ("Transformers and Large Language Models", "Attention, tokenization, context and inference", "Inspect model behavior and build a constrained inference workflow."),
        ("Prompt Engineering and Structured Outputs", "Instruction design, schemas and validation", "Build robust prompts with machine-checked structured outputs."),
        ("RAG and Information Retrieval", "Chunking, embeddings, retrieval and grounding", "Evaluate a retrieval pipeline for relevance and unsupported claims."),
        ("AI Evaluation and Red Teaming", "Test sets, hallucinations, robustness and misuse", "Create adversarial evaluations and report failure patterns."),
        ("AI Security and Privacy", "Prompt injection, data leakage, model supply chain and access", "Harden a synthetic AI application against realistic threats."),
        ("MLOps and Model Deployment", "Versioning, serving, monitoring and rollback", "Build a reproducible model delivery pipeline."),
        ("Responsible AI and Governance", "Fairness, explainability, privacy and accountability", "Audit a model deployment for measurable risks and controls."),
        ("Capstone: Evaluated AI Product", "Data, model, retrieval, evaluation and operations", "Deliver an AI feature with evidence-based evaluation and safeguards."),
    ],
    "redes-sistemas": [
        ("Computer Architecture and Operating Systems", "Processes, memory, filesystems and kernel boundaries", "Diagnose resource and process behavior from system fixtures."),
        ("Linux Administration", "Shell, users, permissions, services and storage", "Automate a hardened Linux administration workflow in a lab."),
        ("Windows Administration and PowerShell", "Services, event logs, identity and policy", "Automate Windows host inventory and configuration auditing."),
        ("Networking Models and Protocols", "OSI, TCP/IP, Ethernet, ARP and ICMP", "Analyze protocol traces and identify layer-specific faults."),
        ("IP Addressing and Subnetting", "CIDR, subnet design, routing and IPv6", "Produce and validate an address plan under strict constraints."),
        ("Switching, VLANs and Layer 2", "MAC learning, trunks, STP and segmentation", "Design segmented switching and diagnose loop scenarios."),
        ("Routing and Network Services", "Static/dynamic routing, DNS, DHCP and NAT", "Resolve multi-subnet routing failures from topology data."),
        ("Wireless and Remote Access", "Wi-Fi security, VPNs and remote access", "Assess a synthetic wireless and remote-access architecture."),
        ("Network Automation and Python", "APIs, parsing, configuration generation and validation", "Build idempotent network automation against mock device interfaces."),
        ("Virtualization and Containers", "Hypervisors, namespaces, images and isolation", "Design a safe isolated lab and audit container boundaries."),
        ("Monitoring and Troubleshooting", "Telemetry, packet capture, baselines and fault isolation", "Correlate performance telemetry and isolate root causes."),
        ("Infrastructure Security", "Firewalls, segmentation, hardening and patching", "Design and test layered controls for a small enterprise network."),
        ("Cloud Networking", "VPCs, security groups, routing and hybrid connectivity", "Audit cloud network paths and least-privilege exposure."),
        ("Resilience, Backup and Operations", "High availability, recovery and operational runbooks", "Validate recovery objectives using simulated outage evidence."),
        ("Capstone: Enterprise Network and Systems", "Architecture, automation, security and operations", "Deliver a documented, secure network design with reproducible validation."),
    ],
}

RESOURCE_LINKS = {
    "ciberseguridad": [
        ("NIST NICE Framework v2.2.0", "https://www.nist.gov/itl/applied-cybersecurity/nice/nice-framework-resource-center"),
        ("OWASP Top 10:2025", "https://owasp.org/Top10/2025/"),
        ("MITRE ATT&CK", "https://attack.mitre.org/"),
        ("PortSwigger Web Security Academy", "https://portswigger.net/web-security"),
        ("OWASP WebGoat", "https://owasp.org/www-project-webgoat/"),
        ("OverTheWire Wargames", "https://overthewire.org/wargames/"),
        ("CyberDefenders Labs", "https://cyberdefenders.org/"),
        ("NIST SP 800-61 Incident Response", "https://csrc.nist.gov/pubs/sp/800/61/r3/final"),
    ],
    "programacion": [
        ("Python Tutorial", "https://docs.python.org/3/tutorial/"),
        ("Exercism", "https://exercism.org/"),
        ("Project Euler", "https://projecteuler.net/"),
        ("MIT OpenCourseWare", "https://ocw.mit.edu/"),
        ("CS50", "https://cs50.harvard.edu/x/"),
    ],
    "frontend": [("MDN Learn Web Development", "https://developer.mozilla.org/en-US/docs/Learn_web_development"), ("web.dev", "https://web.dev/learn/"), ("W3C WAI Tutorials", "https://www.w3.org/WAI/tutorials/")],
    "backend": [("FastAPI Documentation", "https://fastapi.tiangolo.com/"), ("Django Documentation", "https://docs.djangoproject.com/"), ("OWASP Cheat Sheet Series", "https://cheatsheetseries.owasp.org/")],
    "datos": [("Pandas Documentation", "https://pandas.pydata.org/docs/"), ("Kaggle Learn", "https://www.kaggle.com/learn"), ("scikit-learn User Guide", "https://scikit-learn.org/stable/user_guide.html")],
    "bases-datos": [("PostgreSQL Documentation", "https://www.postgresql.org/docs/"), ("Use The Index, Luke", "https://use-the-index-luke.com/"), ("SQLBolt", "https://sqlbolt.com/")],
    "ia": [("Google Machine Learning Crash Course", "https://developers.google.com/machine-learning/crash-course"), ("Hugging Face Course", "https://huggingface.co/learn"), ("scikit-learn User Guide", "https://scikit-learn.org/stable/user_guide.html")],
    "redes-sistemas": [("Cisco Networking Academy", "https://www.netacad.com/"), ("Linux Journey", "https://linuxjourney.com/"), ("PowerShell Documentation", "https://learn.microsoft.com/powershell/")],
}

DIFFICULTY = [
    ("Guided", "Follow a worked example and complete the missing implementation."),
    ("Guided transfer", "Solve a structurally similar case with changed data and constraints."),
    ("Independent foundation", "Implement the task from a written contract without a worked solution."),
    ("Edge-case engineering", "Handle malformed, missing, duplicated and boundary inputs."),
    ("Multi-step reasoning", "Combine at least two concepts and explain design decisions."),
    ("Adversarial conditions", "Defend against hostile or unexpected inputs in the supplied lab."),
    ("Optimization", "Meet explicit time, memory, reliability or maintainability constraints."),
    ("Integration", "Integrate the solution with another component through a defined interface."),
    ("Incident simulation", "Diagnose an unfamiliar scenario and produce reproducible evidence."),
    ("Expert challenge", "Deliver a robust, tested solution and defend trade-offs against a strict rubric."),
]

TASK_SHAPES = [
    ("Implement", "Write the implementation and a focused test suite."),
    ("Debug", "Find the root cause in the supplied broken implementation, fix it and add a regression test."),
    ("Refactor", "Refactor the supplied design without changing its public behavior; prove equivalence with tests."),
    ("Analyze", "Parse the supplied fixture, derive a defensible conclusion and emit a machine-readable report."),
    ("Harden", "Identify trust boundaries, implement controls and demonstrate that negative tests are rejected."),
    ("Optimize", "Measure the baseline, improve the bottleneck and provide before/after evidence."),
    ("Integrate", "Connect two components through the documented contract and handle partial failure."),
    ("Automate", "Create an idempotent automation tool with dry-run behavior and structured logs."),
    ("Investigate", "Reconstruct the scenario from artifacts, separate facts from hypotheses and preserve evidence."),
    ("Design", "Produce an implementation-ready design, executable acceptance checks and a risk analysis."),
]


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def build_area(area_id: str) -> dict[str, Any]:
    """Build 15 strategic modules with 10 distinct, progressively harder tasks each."""
    definitions = AREA_MODULES.get(area_id)
    if not definitions:
        raise KeyError(area_id)
    modules = []
    for module_index, (title, focus, project) in enumerate(definitions, start=1):
        module_id = f"{area_id}-m{module_index:02d}"
        exercises = []
        for number in range(1, 11):
            difficulty, cognitive_demand = DIFFICULTY[number - 1]
            action, deliverable = TASK_SHAPES[number - 1]
            guided = number <= 2
            scenario = (
                f"Case {number:02d}: A team at Northstar Labs has a production-style problem involving "
                f"{focus.lower()}. Your task is to {action.lower()} a solution for this case. "
                f"{project}"
            )
            exercises.append({
                "id": f"{module_id}-e{number:02d}",
                "number": number,
                "title": f"{difficulty}: {action} challenge",
                "difficulty": number,
                "difficulty_label": difficulty,
                "guided": guided,
                "language": "python",
                "scenario": scenario,
                "briefing": (
                    "Worked example and annotated steps are available. Study the input contract, "
                    "trace one example by hand, implement the smallest correct version, then run the tests."
                    if number == 1 else
                    "A partial worked path and hints are available. Transfer the reasoning to this new case; "
                    "do not copy the previous solution."
                    if number == 2 else
                    "No worked solution is shown. Read the contract, identify invariants, implement, test "
                    "boundary cases and explain the trade-offs."
                ),
                "deliverable": deliverable,
                "acceptance_criteria": [
                    "Meets the stated functional contract.",
                    "Handles empty, malformed and boundary inputs safely.",
                    "Includes meaningful tests beyond the happy path.",
                    "Uses clear names, small functions and explicit error handling.",
                ],
                "hints": [
                    "Write down the input and output contract before coding.",
                    "Separate parsing, core logic and reporting.",
                    "Test one normal case, one boundary case and one adversarial case.",
                ] if guided else [
                    "Start from invariants and edge cases, not from a guessed implementation.",
                    "Use small functions and tests to isolate the failing behavior.",
                ],
                "rubric": {"correctness": 45, "edge_cases": 20, "security_or_reliability": 20, "code_quality": 15},
            })
        modules.append({
            "id": module_id,
            "number": module_index,
            "title": title,
            "focus": focus,
            "project": project,
            "reading_required": True,
            "exercises_required": 10,
            "weekly_evaluation_required": True,
            "weekly_evaluation": {
                "id": f"{module_id}-weekly",
                "title": f"Weekly assessment: {title}",
                "unlock_rule": "All 10 practical exercises passed and required reading acknowledged.",
                "format": "scenario_based",
                "minimum_score": 80,
                "questions": [
                    "Diagnose a new scenario using evidence from the module.",
                    "Implement or specify a defensible solution under constraints.",
                    "Explain failure modes, trade-offs and verification strategy.",
                ],
            },
            "exercises": exercises,
        })
    return {
        "id": area_id,
        "module_count": 15,
        "exercise_count": 150,
        "modules": modules,
        "resources": [{"title": title, "url": url} for title, url in RESOURCE_LINKS.get(area_id, [])],
    }


def build_catalog() -> dict[str, Any]:
    areas = [build_area(area_id) for area_id in AREA_MODULES]
    return {
        "version": "2026.11-practical-v1",
        "language_progression": {
            "initial": "Spanish explanations with essential English technical vocabulary.",
            "progressive": "Introduce English documentation, prompts and terminology as demonstrated competence increases.",
            "advanced": "English-first technical reading and scenario briefs, with glossary support.",
            "rule": "Language difficulty must never silently increase the technical assessment difficulty.",
        },
        "requirements": {
            "modules_per_area": 15,
            "practical_exercises_per_module": 10,
            "reading_required": True,
            "weekly_assessment_required": True,
            "unlock": "Reading + 10 passed exercises + passed weekly assessment.",
            "retry": "A failed attempt receives targeted feedback and remains retryable.",
        },
        "areas": areas,
    }


def get_exercise(area_id: str, module_number: int, exercise_number: int) -> dict[str, Any]:
    if not 1 <= module_number <= 15 or not 1 <= exercise_number <= 10:
        raise ValueError("Module and exercise numbers must be between 1 and 15 / 1 and 10.")
    return build_area(area_id)["modules"][module_number - 1]["exercises"][exercise_number - 1]
