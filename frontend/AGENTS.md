# Antigravity 2.0 Execution Rules

## 1. Project Scope and Boundaries
* **Target Environment:** This workspace is strictly scoped to a Vite + TypeScript frontend presentation layer for a No-Limit Texas Hold'em application.
* **Backend Isolation:** The reinforcement learning bot and FastAPI backend are hosted remotely on an EC2 instance. Agents must NEVER attempt to alter server-side game theory logic, routing, or the external Docker networking setup.
* **Directory Restrictions:** * Agents may ONLY read and modify files within the `src/` directory.
  * Agents are explicitly forbidden from modifying `vite.config.ts`, `package.json`, or any `tsconfig.*.json` files unless explicitly instructed by the user.
  * Ignore `node_modules/`, `dist/`, and `.env.example`.

## 2. Agent Roles
### UI Tweaker (Primary)
* **Model Routing:** Gemini 3.5 Flash
* **Primary Task:** Iteratively adjust existing user interface components, layout constraints, and styling.
* **Constraints:** Maintain strict TypeScript typing. Do not alter existing data-fetching mechanisms or API calls to the EC2 backend.
* **Permissions:** Read/Write access is limited strictly to `src/`. Code execution is disabled.

### State Planner
* **Status:** DISABLED. 
* **Reasoning:** Core UI components and backend communication are already established.

### Design Critic (Validation)
* **Model Routing:** Local GPT-OSS (Running via 8GB VRAM allocation)
* **Primary Task:** Asynchronously evaluate the UI Tweaker's layout modifications for visual consistency.
* **Constraints:** Generate validation reports only. Do not perform direct file modifications.

## 3. Workflow and Performance Limits
* **Execution Loop:** Run the UI Tweaker for rapid styling iterations. Pause and clear context before invoking the local Design Critic to ensure stable performance within the 8 GB VRAM limit.
* **Review-Driven Development:** Autonomous overwrites are disabled. All visual modifications require manual user approval before being applied to the `src/` directory.