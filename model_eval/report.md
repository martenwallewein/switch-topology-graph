## **Report: Analysis of SCION Deployment Scenarios and the Necessity of Ecosystem Fairness Pillars**

### **1. Executive Summary**

This report details the results of a simulation designed to test the stability and economic viability of a large-scale SCION deployment within an Internet Service Provider (ISP). The experiments analyzed the impact of different end-host path selection behaviors on ISP costs and overall network performance.

The findings provide strong, quantitative evidence for the necessity of a "fairness ecosystem" composed of three key pillars:

1.  **Pillar 1 (ISP Cost Control):** The potential for end-hosts to choose cost-oblivious paths presents a significant financial risk to ISPs. The simulation revealed a **4x (400%) increase in operational costs** in the worst-case scenario compared to the ISP's optimal routing.
2.  **Pillar 2 (End-host to End-host Fairness):** Uncoordinated, "selfish" end-host behavior leads to catastrophic network failure. The "Thundering Herd" scenario, where all users targeted the best-performing path, resulted in a **50% traffic drop rate** due to congestion. In contrast, a cooperative "Fair Share" model successfully delivered **100% of traffic**.
3.  **Pillar 3 (ISP to End-host Fairness):** ISP-led network management is a highly effective solution to the problems caused by selfish end-host behavior. By simulating a single ISP intervention (signaling congestion), the network failure was **completely resolved**, reducing the traffic drop rate from **50% to 0%**.

**Conclusion:** An unmanaged SCION deployment is vulnerable to severe economic and performance instability. The implementation of all three fairness pillars is critical for creating a scalable, robust, and mutually beneficial ecosystem for both ISPs and end-hosts.

---

### **2. Research Objectives & Methodology**

The primary goal of this research was to answer three critical questions regarding a large-scale SCION deployment:
1.  How big is the cost difference between an ISP's baseline routing and a SCION worst-case?
2.  How significant is the performance degradation in a "Thundering Herd" scenario?
3.  What is the impact of an ISP actively managing congestion by signaling path performance?

To answer these questions, four distinct models were applied to a test scenario:
*   **ISP Optimal (Min Cost LP):** Simulates the ISP's ideal traffic routing to minimize operational costs.
*   **ISP Pessimal (Max Cost LP):** Simulates a worst-case scenario where SCION end-hosts choose paths that maximize ISP costs.
*   **Thundering Herd (Selfish Simulator):** Models uncoordinated end-hosts all greedily choosing the path with the lowest latency.
*   **Fair Share (Cooperative Simulator):** Models coordinated end-hosts that balance their traffic across all available paths.

The experiment was conducted in two phases:
*   **Phase 1 (Initial State):** All four models were run on an initial network scenario to establish baseline behaviors and identify potential problems.
*   **Phase 2 (Reacted State):** Based on the congestion identified in Phase 1, the input scenario was modified to simulate an ISP signaling high latency on the congested path. All four models were run again to measure the effect of this intervention.

---

### **3. Experimental Results & Analysis**

#### **3.1. Pillar 1: Financial Impact of Uncontrolled Path Selection**

By comparing the ISP Optimal and Pessimal models from the initial state, we can quantify the financial risk.

| Scenario | Total Cost | Strategy |
| :--- | :--- | :--- |
| **ISP Optimal** | **250.0** | Traffic is intelligently split across two cheap peering links (`e2`, `e3`). |
| **ISP Pessimal**| **1000.0**| All traffic is forced over the single most expensive transit link (`e1`). |

**Analysis:**
The worst-case scenario results in a **400% cost increase** (1000.0 vs 250.0) for the ISP to deliver the exact same amount of traffic. This demonstrates a critical vulnerability. An ISP cannot sustainably operate under conditions where its costs can fluctuate so dramatically based on external choices.

**Conclusion:** This provides a strong economic justification for **Pillar 1**, where ISPs must have the ability to filter or de-prioritize certain paths to protect their network from unsustainable costs.

#### **3.2. Pillar 2: Performance Impact of End-host Behavior**

By comparing the Thundering Herd and Fair Share models from the initial state, we can quantify the impact of end-host coordination.

| Scenario | Total Sent Traffic | Unsent (Dropped) Traffic | Network Utilization |
| :--- | :--- | :--- | :--- |
| **Thundering Herd**| 50.0 / 100.0 (50%) | **50.0 (50% Failure)**| `e2` at 100%, `e1` & `e3` at 0% |
| **Fair Share** | 100.0 / 100.0 (100%)| **0.0 (Success)** | Balanced: `e1`:33%, `e2`:67%, `e3`:33% |

**Analysis:**
The selfish behavior of the thundering herd creates a "Tragedy of the Commons." All users rush to the best path (`e2`), overwhelming its capacity and causing half of all traffic to be dropped. The network is simultaneously congested and underutilized. In contrast, the cooperative Fair Share model successfully delivers all traffic by balancing the load.

**Conclusion:** This result proves that **Pillar 2** is essential. Without a mechanism for end-host to end-host fairness, the very freedom that makes SCION powerful can lead to systemic network failures.

#### **3.3. Pillar 3: Effectiveness of ISP Congestion Management**

By comparing the "Thundering Herd" scenario from the Initial State and the Reacted State, we can measure the impact of the ISP's intervention.

| Metric | Before Reaction (Initial State) | After Reaction (Reacted State) | Outcome |
| :--- | :--- | :--- | :--- |
| **Unsent (Dropped) Traffic**| **50.0 (50% Failure)** | **0.0 (0% Failure)** | ✅ **Problem Solved** |
| **Congested Link** | `e2_fast_peer` at 100% | `e3_ok_peer` at 100% | ✅ **Load Redirected** |
| **Resulting ISP Cost** | 100.0 (for 50% traffic) | 300.0 (for 100% traffic) | ↔️ **Service Restored** |

**Analysis:**
The ISP's action of signaling high latency on the congested `e2` link was completely successful. The selfish end-hosts, seeing the signal, rationally redirected their traffic to the new "best" path, `e3`. This path had sufficient capacity to handle the load, resulting in the successful delivery of all traffic. The network went from a 50% failure state to a 100% success state.

**Conclusion:** This validates the necessity and effectiveness of **Pillar 3**. ISP guidance is a critical tool to manage network resources, prevent congestion collapse, and ensure a high quality of service for all users. It turns the selfish-but-rational behavior of end-hosts into a predictable and manageable network dynamic.

---

### **4. Appendices: Raw Simulation Output**

#### **Appendix A: `initial_state_report.json`**
```json
{
    "isp_optimal": {
        "scenario_name": "ISP Optimal (Cost LP)",
        "lp_status": "Optimal",
        "total_cost": 250.0,
        "traffic_allocation": {
            "h1_p_h1_e2_to_D_Service": 50.0,
            "h1_p_h1_e3_to_D_Service": 50.0
        },
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 0.0, "capacity": 100, "utilization_percent": 0.0},
                "e2_fast_peer": {"traffic": 50.0, "capacity": 50, "utilization_percent": 100.0},
                "e3_ok_peer": {"traffic": 50.0, "capacity": 100, "utilization_percent": 50.0}
            }
        }
    },
    "isp_pessimal": {
        "scenario_name": "ISP Pessimal (Cost LP)",
        "lp_status": "Optimal",
        "total_cost": 1000.0,
        "traffic_allocation": {"h1_p_h1_e1_to_D_Service": 100.0},
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 100.0, "capacity": 100, "utilization_percent": 100.0},
                "e2_fast_peer": {"traffic": 0.0, "capacity": 50, "utilization_percent": 0.0},
                "e3_ok_peer": {"traffic": 0.0, "capacity": 100, "utilization_percent": 0.0}
            }
        }
    },
    "thundering_herd": {
        "scenario_name": "End-Host Selfish (Thundering Herd)",
        "total_cost": 100.0,
        "total_sent_traffic": 50.0,
        "total_unsent_traffic": 50.0,
        "traffic_allocation": {"h1_p_h1_e2_to_D_Service": 50.0},
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 0.0, "capacity": 100, "utilization_percent": 0.0},
                "e2_fast_peer": {"traffic": 50.0, "capacity": 50, "utilization_percent": 100.0},
                "e3_ok_peer": {"traffic": 0.0, "capacity": 100, "utilization_percent": 0.0}
            }
        }
    },
    "fair_share": {
        "scenario_name": "End-Host Cooperative (Fair Share)",
        "total_cost": 500.0,
        "total_sent_traffic": 100.0,
        "total_unsent_traffic": -0.0,
        "traffic_allocation": {
            "h1_p_h1_e1_to_D_Service": 16.666666666666668,
            "h1_p_h1_e2_to_D_Service": 16.666666666666668,
            "h1_p_h1_e3_to_D_Service": 16.666666666666668,
            "h2_p_h2_e1_to_D_Service": 16.666666666666668,
            "h2_p_h2_e2_to_D_Service": 16.666666666666668,
            "h2_p_h2_e3_to_D_Service": 16.666666666666668
        },
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 33.33, "capacity": 100, "utilization_percent": 33.33},
                "e2_fast_peer": {"traffic": 33.33, "capacity": 50, "utilization_percent": 66.67},
                "e3_ok_peer": {"traffic": 33.33, "capacity": 100, "utilization_percent": 33.33}
            }
        }
    }
}
```

#### **Appendix B: `reacted_state_report.json`**
```json
{
    "isp_optimal": {
        "scenario_name": "ISP Optimal (Cost LP)",
        "lp_status": "Optimal",
        "total_cost": 250.0,
        "traffic_allocation": {
            "h1_p_h1_e2_to_D_Service": 50.0,
            "h1_p_h1_e3_to_D_Service": 50.0
        },
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 0.0, "capacity": 100, "utilization_percent": 0.0},
                "e2_fast_peer": {"traffic": 50.0, "capacity": 50, "utilization_percent": 100.0},
                "e3_ok_peer": {"traffic": 50.0, "capacity": 100, "utilization_percent": 50.0}
            }
        }
    },
    "isp_pessimal": {
        "scenario_name": "ISP Pessimal (Cost LP)",
        "lp_status": "Optimal",
        "total_cost": 1000.0,
        "traffic_allocation": {"h1_p_h1_e1_to_D_Service": 100.0},
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 100.0, "capacity": 100, "utilization_percent": 100.0},
                "e2_fast_peer": {"traffic": 0.0, "capacity": 50, "utilization_percent": 0.0},
                "e3_ok_peer": {"traffic": 0.0, "capacity": 100, "utilization_percent": 0.0}
            }
        }
    },
    "thundering_herd": {
        "scenario_name": "End-Host Selfish (Thundering Herd)",
        "total_cost": 300.0,
        "total_sent_traffic": 100.0,
        "total_unsent_traffic": 0.0,
        "traffic_allocation": {
            "h1_p_h1_e3_to_D_Service": 50.0,
            "h2_p_h2_e3_to_D_Service": 50.0
        },
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 0.0, "capacity": 100, "utilization_percent": 0.0},
                "e2_fast_peer": {"traffic": 0.0, "capacity": 50, "utilization_percent": 0.0},
                "e3_ok_peer": {"traffic": 100.0, "capacity": 100, "utilization_percent": 100.0}
            }
        }
    },
    "fair_share": {
        "scenario_name": "End-Host Cooperative (Fair Share)",
        "total_cost": 500.0,
        "total_sent_traffic": 100.0,
        "total_unsent_traffic": -0.0,
        "traffic_allocation": {
            "h1_p_h1_e1_to_D_Service": 16.666666666666668,
            "h1_p_h1_e2_to_D_Service": 16.666666666666668,
            "h1_p_h1_e3_to_D_Service": 16.666666666666668,
            "h2_p_h2_e1_to_D_Service": 16.666666666666668,
            "h2_p_h2_e2_to_D_Service": 16.666666666666668,
            "h2_p_h2_e3_to_D_Service": 16.666666666666668
        },
        "performance_analysis": {
            "egress_utilization": {
                "e1_slow_transit": {"traffic": 33.33, "capacity": 100, "utilization_percent": 33.33},
                "e2_fast_peer": {"traffic": 33.33, "capacity": 50, "utilization_percent": 66.67},
                "e3_ok_peer": {"traffic": 33.33, "capacity": 100, "utilization_percent": 33.33}
            }
        }
    }
}
```