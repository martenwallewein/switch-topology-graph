# Adversarial and Optimal Traffic Allocation Math Model (Sunk Cost Version)

This document specifies a linear programming (LP) model designed to determine the traffic allocation from end-hosts to destinations that results in either the maximum (pessimal) or minimum (optimal) cost for a network operator. The model considers end-host uplink capacities, egress interface capacities, traffic demands for specific destinations, and a cost structure that includes both per-bandwidth (variable) costs and the **sunk fixed costs** for egress link availability.

### Objective

The primary goal is to find the traffic distribution that either **maximizes** or **minimizes** the total cost incurred by the local network operator. This cost is composed of two parts:
1.  A **variable cost** proportional to the amount of traffic sent over each egress interface.
2.  A **fixed sunk cost** for maintaining the availability of each egress link, which is incurred regardless of traffic volume.

Since the total fixed cost is constant, the optimization focuses on the variable cost. The final total cost is then calculated by adding the constant fixed costs.

*   **Maximization (`ISP Pessimal`):** Represents an adversarial scenario where end-hosts coordinate to route traffic over the most expensive variable-cost links, inflicting the highest possible operational cost on the operator.
*   **Minimization (`ISP Optimal`):** Represents a cooperative or operator-controlled scenario where traffic is routed in the most cost-effective way possible to minimize variable costs.

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
*   `BaseCost_e`: The **fixed sunk cost** for having egress interface `e ∈ E` available for use. This cost is always incurred.
*   `T_d`: The total traffic demand that must be sent to destination `d ∈ D`. This is a strict requirement.
*   `Egress(p)`: A function that maps a path `p ∈ P` to the specific egress interface `e ∈ E` it utilizes.
*   `Reachable(e, d)`: A boolean function indicating if destination `d ∈ D` is reachable through egress interface `e ∈ E`.

### Decision Variables

*   `x_{hpd}`: A continuous, non-negative variable representing the amount of traffic sent by end-host `h ∈ H`, over its available path `p ∈ P_h`, to destination `d ∈ D`.

*(Note: The binary variable `y_e` is no longer needed in this model.)*

### Objective Function

The objective is to minimize or maximize the **total variable cost** `Z_var`. The total fixed cost is a constant and is added after the optimization is complete.

**Minimize or Maximize:**
`Z_var = Σ_{h∈H} Σ_{p∈P_h} Σ_{d∈D} (x_{hpd} * Cost_{Egress(p)})`

The final total cost `Z_total` is then calculated as:
`Z_total = Z_var + Σ_{e∈E} BaseCost_e`

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

4.  **Non-negativity Constraint:**
    *   `x_{hpd} ≥ 0` for all `h ∈ H`, `p ∈ P_h`, `d ∈ D`.

*(Note: The "Big M" constraint is no longer required as there are no binary variables to link.)*

### Summary of the LP Formulation

**Optimize for (Minimize or Maximize):**
`Z_var = Σ_{h,p,d} (x_{hpd} * Cost_{Egress(p)})`

**Subject to:**
1.  `Σ_{h,p} x_{hpd} = T_d` (for all `d ∈ D`)
2.  `Σ_{p,d} x_{hpd} ≤ U_h` (for all `h ∈ H`)
3.  `Σ_{h,p,d | Egress(p)=e} x_{hpd} ≤ Cap_e` (for all `e ∈ E`)
4.  `x_{hpd} ≥ 0`

### Key Changes in this Model Version

*   **Realistic Sunk Cost Modeling:** This version treats fixed costs as sunk costs that are always incurred. This is a more accurate representation of how physical network infrastructure is billed and removes the need for the model to "decide" whether to activate a link.
*   **Simplification from MILP to LP:** By removing the binary variables (`y_e`) and the associated "Big M" constraint, the problem is simplified from a Mixed-Integer Linear Program (MILP) to a standard Linear Program (LP).
*   **Improved Computational Efficiency:** LPs are fundamentally less complex and significantly faster to solve than MILPs, especially as the number of egress links grows. This makes the model more scalable.
*   **Retained Features:** The model remains destination-aware, enforces strict traffic demands, and can still be used for both cost minimization (ISP-optimal) and maximization (ISP-pessimal) scenarios to find the best- and worst-case outcomes for variable costs.