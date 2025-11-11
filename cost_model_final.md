Here is the updated formal description of the mathematical model, reflecting the new implementation in the provided Python script.

***

# Adversarial and Optimal Traffic Allocation Math Model

This document specifies a linear programming (LP) model designed to determine the traffic allocation from end-hosts to destinations that results in either the maximum (pessimal) or minimum (optimal) cost for a network operator. The model considers end-host uplink capacities, egress interface capacities, traffic demands for specific destinations, and a cost structure that includes both per-bandwidth (variable) and fixed-use (base) costs for egress links.

### Objective

The primary goal is to find the traffic distribution that either **maximizes** or **minimizes** the total cost incurred by the local network operator. This cost is composed of two parts: a variable cost proportional to the amount of traffic sent over each egress interface and a fixed base cost applied if an egress interface is used at all.

*   **Maximization (`ISP Pessimal`):** Represents an adversarial scenario where end-hosts coordinate to inflict the highest possible cost on the operator while still meeting their traffic demands.
*   **Minimization (`ISP Optimal`):** Represents a cooperative or operator-controlled scenario where traffic is routed in the most cost-effective way possible.

### Entities & Data

#### 1. Sets
*   `H`: The set of all end-hosts within the local AS.
*   `E`: The set of all egress interfaces in the local AS.
*   `D`: The set of all final destinations for the traffic.
*   `P_h`: For each end-host `h ∈ H`, this is the subset of available SCION paths that `h` can use.
*   `P`: The set of all possible paths, where `P = ⋃_{h ∈ H} P_h`.

#### 2. Parameters (Given Data)
*   `U_h`: The total uplink capacity for each end-host `h ∈ H`.
*   `Cap_e`: The total traffic capacity of each egress interface `e ∈ E`.
*   `Cost_e`: The variable cost per unit of traffic sent through egress interface `e ∈ E`.
*   `BaseCost_e`: The fixed base cost incurred if egress interface `e ∈ E` is used at all (i.e., carries any amount of traffic).
*   `T_d`: The total traffic demand that must be sent to destination `d ∈ D`. This is a strict requirement.
*   `Egress(p)`: A function that maps a path `p ∈ P` to the specific egress interface `e ∈ E` it utilizes.
*   `Reachable(e, d)`: A boolean function indicating if destination `d ∈ D` is reachable through egress interface `e ∈ E`.

### Decision Variables

*   `x_{hpd}`: A continuous, non-negative variable representing the amount of traffic sent by end-host `h ∈ H`, over its available path `p ∈ P_h`, to destination `d ∈ D`.
*   `y_e`: A binary variable (`{0, 1}`) for each egress interface `e ∈ E`. `y_e` is equal to `1` if the total traffic flowing through egress `e` is greater than zero, and `0` otherwise.

### Objective Function

The objective is to minimize or maximize the total cost `Z`, which is the sum of the per-bandwidth costs and the fixed base costs.

**Minimize or Maximize:**
`Z = Σ_{h∈H} Σ_{p∈P_h} Σ_{d∈D} (x_{hpd} * Cost_{Egress(p)}) + Σ_{e∈E} (y_e * BaseCost_e)`

### Constraints

1.  **Traffic Demand Satisfaction:** For each destination `d`, the total traffic sent to it from all end-hosts over all valid paths must exactly equal the specified demand for that destination.
    *   For each `d ∈ D`:
        `Σ_{h∈H} Σ_{p∈P_h such that Reachable(Egress(p), d)} x_{hpd} = T_d`

2.  **End-host Uplink Capacity:** For each end-host `h`, the total traffic it sends across all its paths to all destinations cannot exceed its uplink capacity.
    *   For each `h ∈ H`:
        `Σ_{p∈P_h} Σ_{d∈D} x_{hpd} ≤ U_h`

3.  **Egress Interface Capacity:** For each egress interface `e`, the total traffic flowing through it from all end-hosts to all destinations cannot exceed its capacity.
    *   For each `e ∈ E`:
        `Σ_{h∈H} Σ_{p∈P_h such that Egress(p)=e} Σ_{d∈D} x_{hpd} ≤ Cap_e`

4.  **Fixed Cost Activation ("Big M" Constraint):** This constraint links the continuous traffic variable `x_{hpd}` with the binary variable `y_e`. It forces `y_e` to be `1` if any traffic flows through egress `e`.
    *   For each `e ∈ E`:
        `Σ_{h∈H} Σ_{p∈P_h such that Egress(p)=e} Σ_{d∈D} x_{hpd} ≤ Cap_e * y_e`
    *(Note: The egress capacity `Cap_e` is used as a sufficiently large constant "M" for this constraint, as no more traffic than its capacity can flow through it.)*

5.  **Non-negativity and Binary Constraints:**
    *   `x_{hpd} ≥ 0` for all `h ∈ H`, `p ∈ P_h`, `d ∈ D`.
    *   `y_e ∈ {0, 1}` for all `e ∈ E`.

### Summary of the LP Formulation

**Optimize for (Minimize or Maximize):**
`Z = Σ_{h,p,d} (x_{hpd} * Cost_{Egress(p)}) + Σ_{e} (y_e * BaseCost_e)`

**Subject to:**
1.  `Σ_{h,p} x_{hpd} = T_d` (for all `d ∈ D`)
2.  `Σ_{p,d} x_{hpd} ≤ U_h` (for all `h ∈ H`)
3.  `Σ_{h,p,d | Egress(p)=e} x_{hpd} ≤ Cap_e` (for all `e ∈ E`)
4.  `Σ_{h,p,d | Egress(p)=e} x_{hpd} ≤ Cap_e * y_e` (for all `e ∈ E`)
5.  `x_{hpd} ≥ 0`
6.  `y_e ∈ {0, 1}`

### Key Changes from Previous Model

*   **Destination-Awareness:** The model now routes traffic to specific final destinations (`D`) rather than just to egress interfaces, making it more realistic.
*   **Strict Traffic Demands:** The model must satisfy a precise traffic demand for each destination (`T_d`), changing the problem from allocating a flexible traffic pool to fulfilling specific routing requirements.
*   **Mixed-Integer Programming:** The introduction of binary variables (`y_e`) and fixed base costs (`BaseCost_e`) transforms the problem into a Mixed-Integer Linear Program (MILP). This allows for more complex cost structures where activating a link has a cost in addition to the cost of the traffic volume.
*   **Dual Optimization Goal:** The model is explicitly designed to be solved for both cost minimization (ISP-optimal) and maximization (ISP-pessimal), providing a direct comparison between the best-case and worst-case cost scenarios for the operator.