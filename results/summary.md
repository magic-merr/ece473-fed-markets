# Fed decision markets: Kalshi vs Polymarket vs fed funds futures

Stale rule: N = 3 days, max spread = 0.10. Generated 2026-11-12.

## Coverage

| venue           |   meeting_days |   meetings | first      | last       |
|:----------------|---------------:|-----------:|:-----------|:-----------|
| kalshi          |           4670 |         40 | 2022-11-02 | 2026-11-12 |
| kalshi_decision |           4506 |         38 | 2023-04-08 | 2026-11-12 |
| kalshi_ladder   |           1465 |         32 | 2022-11-02 | 2026-11-12 |
| polymarket      |           2621 |         28 | 2023-11-14 | 2026-11-12 |
| zq              |            754 |          5 | 2026-01-02 | 2026-11-12 |

## Outcomes

| meeting    |   pre_upper |   post_upper |   change_bps | decision   |
|:-----------|------------:|-------------:|-------------:|:-----------|
| 2023-02-01 |       4.500 |        4.750 |           25 | hike       |
| 2023-03-22 |       4.750 |        5.000 |           25 | hike       |
| 2023-05-03 |       5.000 |        5.250 |           25 | hike       |
| 2023-06-14 |       5.250 |        5.250 |            0 | hold       |
| 2023-07-26 |       5.250 |        5.500 |           25 | hike       |
| 2023-09-20 |       5.500 |        5.500 |            0 | hold       |
| 2023-11-01 |       5.500 |        5.500 |            0 | hold       |
| 2023-12-13 |       5.500 |        5.500 |            0 | hold       |
| 2024-01-31 |       5.500 |        5.500 |            0 | hold       |
| 2024-03-20 |       5.500 |        5.500 |            0 | hold       |
| 2024-05-01 |       5.500 |        5.500 |            0 | hold       |
| 2024-06-12 |       5.500 |        5.500 |            0 | hold       |
| 2024-07-31 |       5.500 |        5.500 |            0 | hold       |
| 2024-09-18 |       5.500 |        5.000 |          -50 | cut        |
| 2024-11-07 |       5.000 |        4.750 |          -25 | cut        |
| 2024-12-18 |       4.750 |        4.500 |          -25 | cut        |
| 2025-01-29 |       4.500 |        4.500 |            0 | hold       |
| 2025-03-19 |       4.500 |        4.500 |            0 | hold       |
| 2025-05-07 |       4.500 |        4.500 |            0 | hold       |
| 2025-06-18 |       4.500 |        4.500 |            0 | hold       |
| 2025-07-30 |       4.500 |        4.500 |            0 | hold       |
| 2025-09-17 |       4.500 |        4.250 |          -25 | cut        |
| 2025-10-29 |       4.250 |        4.000 |          -25 | cut        |
| 2025-12-10 |       4.000 |        3.750 |          -25 | cut        |
| 2026-01-28 |       3.750 |        3.750 |            0 | hold       |
| 2026-03-18 |       3.750 |        3.750 |            0 | hold       |
| 2026-04-29 |       3.750 |        3.750 |            0 | hold       |
| 2026-06-17 |       3.750 |        3.750 |            0 | hold       |
| 2026-07-29 |       3.750 |        3.750 |            0 | hold       |
| 2026-09-16 |       3.750 |        4.000 |           25 | hike       |
| 2026-10-28 |       4.000 |        4.000 |            0 | hold       |

## Pairwise Agreement

| pair                | horizon   |   days |   meetings |   mean_diff_p_hold |   mae_p_hold |   mean_diff_p_cut |   mae_p_cut |   rmse_exp_change_bps |   corr_exp_change |   share_abs_gap_gt_5pp |
|:--------------------|:----------|-------:|-----------:|-------------------:|-------------:|------------------:|------------:|----------------------:|------------------:|-----------------------:|
| kalshi - polymarket | 1-7d      |    161 |         24 |             -0.005 |        0.012 |            -0.001 |       0.010 |                 0.538 |             1.000 |                  0.000 |
| kalshi - polymarket | 8-30d     |    531 |         25 |             -0.002 |        0.017 |             0.000 |       0.013 |                 0.825 |             0.997 |                  0.028 |
| kalshi - polymarket | 31-90d    |    767 |         22 |             -0.010 |        0.019 |             0.006 |       0.015 |                 0.956 |             0.997 |                  0.051 |
| kalshi - polymarket | >90d      |    464 |         12 |              0.001 |        0.031 |             0.002 |       0.028 |                 1.809 |             0.980 |                  0.248 |
| kalshi - polymarket | all       |   1923 |         28 |             -0.005 |        0.021 |             0.003 |       0.017 |                 1.169 |             0.995 |                  0.088 |
| kalshi - zq         | 1-7d      |      5 |          1 |              0.013 |        0.017 |             0.010 |       0.010 |                 0.919 |             0.965 |                  0.000 |
| kalshi - zq         | 8-30d     |     21 |          2 |              0.022 |        0.027 |             0.010 |       0.010 |                 1.429 |             0.995 |                  0.095 |
| kalshi - zq         | 31-90d    |     61 |          3 |              0.043 |        0.053 |             0.021 |       0.021 |                 1.931 |             0.979 |                  0.590 |
| kalshi - zq         | >90d      |    378 |          4 |             -0.095 |        0.142 |             0.144 |       0.144 |                 6.293 |             0.755 |                  0.944 |
| kalshi - zq         | all       |    465 |          5 |             -0.070 |        0.124 |             0.120 |       0.120 |                 5.725 |             0.857 |                  0.849 |
| polymarket - zq     | 1-7d      |      5 |          1 |              0.025 |        0.026 |             0.002 |       0.002 |                 0.778 |             0.914 |                  0.200 |
| polymarket - zq     | 8-30d     |     21 |          2 |              0.022 |        0.024 |             0.006 |       0.006 |                 1.165 |             0.997 |                  0.095 |
| polymarket - zq     | 31-90d    |     61 |          3 |              0.039 |        0.049 |             0.017 |       0.017 |                 1.828 |             0.978 |                  0.508 |
| polymarket - zq     | >90d      |    112 |          4 |             -0.052 |        0.088 |             0.101 |       0.101 |                 4.309 |             0.860 |                  0.884 |
| polymarket - zq     | all       |    199 |          5 |             -0.015 |        0.067 |             0.063 |       0.063 |                 3.411 |             0.953 |                  0.668 |

## Accuracy Brier

| venue      |   horizon_days |   meetings |   brier |   mean_p_realized |   meetings_common_kalshi_poly |   brier_common |
|:-----------|---------------:|-----------:|--------:|------------------:|------------------------------:|---------------:|
| kalshi     |              1 |         31 |   0.009 |             0.953 |                            24 |          0.009 |
| polymarket |              1 |         24 |   0.007 |             0.968 |                            24 |          0.007 |
| zq         |              1 |          1 |   0.007 |             0.940 |                             1 |          0.007 |
| kalshi     |              7 |         31 |   0.030 |             0.919 |                            23 |          0.028 |
| polymarket |              7 |         23 |   0.028 |             0.934 |                            23 |          0.028 |
| zq         |              7 |          1 |   0.051 |             0.840 |                             1 |          0.051 |
| kalshi     |             14 |         31 |   0.035 |             0.909 |                            23 |          0.038 |
| polymarket |             14 |         23 |   0.036 |             0.912 |                            23 |          0.036 |
| zq         |             14 |          1 |   0.231 |             0.660 |                             1 |          0.231 |
| kalshi     |             30 |         31 |   0.122 |             0.816 |                            20 |          0.156 |
| polymarket |             30 |         20 |   0.152 |             0.799 |                            20 |          0.152 |
| zq         |             30 |          1 |   0.980 |             0.300 |                             1 |          0.980 |
| kalshi     |             60 |         10 |   0.180 |             0.738 |                             9 |          0.200 |
| polymarket |             60 |         17 |   0.213 |             0.707 |                             9 |          0.193 |
| zq         |             60 |          0 | nan     |           nan     |                             0 |        nan     |

## Kalshi Liquidity

| kind     | horizon   |   contract_days |   median_spread |   p90_spread |   median_taker_fee |   median_maker_fee |   median_round_trip_taker |   fee_pct_of_price |   share_days_traded |   median_volume_when_traded |   median_oi |
|:---------|:----------|----------------:|----------------:|-------------:|-------------------:|-------------------:|--------------------------:|-------------------:|--------------------:|----------------------------:|------------:|
| decision | 1-7d      |             132 |           0.010 |        0.030 |              0.005 |              0.001 |                     0.027 |              0.029 |               0.992 |                  209481.000 | 2870308.625 |
| decision | 8-30d     |             847 |           0.010 |        0.040 |              0.008 |              0.002 |                     0.031 |              0.036 |               0.981 |                   50319.000 |  977992.940 |
| decision | 31-90d    |            1960 |           0.020 |        0.060 |              0.011 |              0.003 |                     0.040 |              0.044 |               0.871 |                    3297.500 |   35741.510 |
| decision | >90d      |           12717 |           0.060 |        0.100 |              0.011 |              0.003 |                     0.088 |              0.055 |               0.227 |                      45.720 |     162.000 |
| level    | 1-7d      |              74 |           0.020 |        0.058 |              0.007 |              0.002 |                     0.033 |              0.032 |               0.973 |                   18850.500 |  142464.000 |
| level    | 8-30d     |             513 |           0.020 |        0.070 |              0.008 |              0.002 |                     0.037 |              0.036 |               0.904 |                    5695.500 |   76915.000 |
| level    | 31-90d    |            4195 |           0.040 |        0.090 |              0.008 |              0.002 |                     0.060 |              0.019 |               0.575 |                     643.000 |   12064.000 |
| level    | >90d      |           51641 |           0.070 |        0.130 |              0.011 |              0.003 |                     0.092 |              0.027 |               0.224 |                      37.000 |     598.000 |

## Price Source Shares

| venue      | horizon   |   contract_days |   share_quote |   share_bound |   share_trade |   share_stale |
|:-----------|:----------|----------------:|--------------:|--------------:|--------------:|--------------:|
| kalshi     | 1-7d      |            3437 |         0.162 |         0.519 |         0.002 |         0.317 |
| kalshi     | 8-30d     |           11333 |         0.246 |         0.432 |         0.008 |         0.314 |
| kalshi     | 31-90d    |           26368 |         0.403 |         0.259 |         0.032 |         0.306 |
| kalshi     | >90d      |          133322 |         0.491 |         0.035 |         0.079 |         0.395 |
| kalshi     | all       |          174460 |         0.456 |         0.104 |         0.066 |         0.375 |
| polymarket | 1-7d      |             805 |         0.000 |         0.000 |         0.856 |         0.144 |
| polymarket | 8-30d     |            2657 |         0.000 |         0.000 |         0.855 |         0.145 |
| polymarket | 31-90d    |            5452 |         0.000 |         0.000 |         0.932 |         0.068 |
| polymarket | >90d      |            3787 |         0.000 |         0.000 |         0.971 |         0.029 |
| polymarket | all       |           12701 |         0.000 |         0.000 |         0.922 |         0.078 |

## Stale Rule Sensitivity

|   N_days |   max_spread | tick_bound   | metric                          |      n |      value |
|---------:|-------------:|:-------------|:--------------------------------|-------:|-----------:|
|        1 |        0.050 | True         | kalshi_meeting_days             |     40 |   2802.000 |
|        1 |        0.050 | True         | polymarket_meeting_days         |     28 |   2576.000 |
|        1 |        0.050 | True         | zq_meeting_days                 |      5 |    754.000 |
|        1 |        0.050 | True         | kalshi_contract_days_usable     | 174460 |  67469.000 |
|        1 |        0.050 | True         | kalshi_vs_poly_mae_p_hold       |   1687 |      0.019 |
|        1 |        0.050 | True         | kalshi_vs_poly_mean_diff_p_hold |   1687 |     -0.005 |
|        1 |        0.050 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        1 |        0.050 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        1 |        0.050 | True         | kalshi_brier_common_7d          |     23 |      0.028 |
|        1 |        0.050 | True         | polymarket_brier_common_7d      |     23 |      0.028 |
|        1 |        0.050 | True         | kalshi_brier_common_30d         |     20 |      0.155 |
|        1 |        0.050 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        1 |        0.100 | True         | kalshi_meeting_days             |     40 |   4376.000 |
|        1 |        0.100 | True         | polymarket_meeting_days         |     28 |   2576.000 |
|        1 |        0.100 | True         | zq_meeting_days                 |      5 |    754.000 |
|        1 |        0.100 | True         | kalshi_contract_days_usable     | 174460 |  97563.000 |
|        1 |        0.100 | True         | kalshi_vs_poly_mae_p_hold       |   1869 |      0.020 |
|        1 |        0.100 | True         | kalshi_vs_poly_mean_diff_p_hold |   1869 |     -0.005 |
|        1 |        0.100 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        1 |        0.100 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        1 |        0.100 | True         | kalshi_brier_common_7d          |     23 |      0.028 |
|        1 |        0.100 | True         | polymarket_brier_common_7d      |     23 |      0.028 |
|        1 |        0.100 | True         | kalshi_brier_common_30d         |     20 |      0.156 |
|        1 |        0.100 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        1 |        0.200 | True         | kalshi_meeting_days             |     40 |   4552.000 |
|        1 |        0.200 | True         | polymarket_meeting_days         |     28 |   2576.000 |
|        1 |        0.200 | True         | zq_meeting_days                 |      5 |    754.000 |
|        1 |        0.200 | True         | kalshi_contract_days_usable     | 174460 | 101772.000 |
|        1 |        0.200 | True         | kalshi_vs_poly_mae_p_hold       |   1877 |      0.020 |
|        1 |        0.200 | True         | kalshi_vs_poly_mean_diff_p_hold |   1877 |     -0.005 |
|        1 |        0.200 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        1 |        0.200 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        1 |        0.200 | True         | kalshi_brier_common_7d          |     23 |      0.028 |
|        1 |        0.200 | True         | polymarket_brier_common_7d      |     23 |      0.028 |
|        1 |        0.200 | True         | kalshi_brier_common_30d         |     20 |      0.157 |
|        1 |        0.200 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        3 |        0.050 | True         | kalshi_meeting_days             |     40 |   3113.000 |
|        3 |        0.050 | True         | polymarket_meeting_days         |     28 |   2621.000 |
|        3 |        0.050 | True         | zq_meeting_days                 |      5 |    754.000 |
|        3 |        0.050 | True         | kalshi_contract_days_usable     | 174460 |  80680.000 |
|        3 |        0.050 | True         | kalshi_vs_poly_mae_p_hold       |   1759 |      0.021 |
|        3 |        0.050 | True         | kalshi_vs_poly_mean_diff_p_hold |   1759 |     -0.005 |
|        3 |        0.050 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        3 |        0.050 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        3 |        0.050 | True         | kalshi_brier_common_7d          |     23 |      0.028 |
|        3 |        0.050 | True         | polymarket_brier_common_7d      |     23 |      0.028 |
|        3 |        0.050 | True         | kalshi_brier_common_30d         |     20 |      0.155 |
|        3 |        0.050 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        3 |        0.100 | True         | kalshi_meeting_days             |     40 |   4670.000 |
|        3 |        0.100 | True         | polymarket_meeting_days         |     28 |   2621.000 |
|        3 |        0.100 | True         | zq_meeting_days                 |      5 |    754.000 |
|        3 |        0.100 | True         | kalshi_contract_days_usable     | 174460 | 109109.000 |
|        3 |        0.100 | True         | kalshi_vs_poly_mae_p_hold       |   1923 |      0.021 |
|        3 |        0.100 | True         | kalshi_vs_poly_mean_diff_p_hold |   1923 |     -0.005 |
|        3 |        0.100 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        3 |        0.100 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        3 |        0.100 | True         | kalshi_brier_common_7d          |     23 |      0.028 |
|        3 |        0.100 | True         | polymarket_brier_common_7d      |     23 |      0.028 |
|        3 |        0.100 | True         | kalshi_brier_common_30d         |     20 |      0.156 |
|        3 |        0.100 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        3 |        0.200 | True         | kalshi_meeting_days             |     40 |   4826.000 |
|        3 |        0.200 | True         | polymarket_meeting_days         |     28 |   2621.000 |
|        3 |        0.200 | True         | zq_meeting_days                 |      5 |    754.000 |
|        3 |        0.200 | True         | kalshi_contract_days_usable     | 174460 | 112984.000 |
|        3 |        0.200 | True         | kalshi_vs_poly_mae_p_hold       |   1932 |      0.021 |
|        3 |        0.200 | True         | kalshi_vs_poly_mean_diff_p_hold |   1932 |     -0.004 |
|        3 |        0.200 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        3 |        0.200 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        3 |        0.200 | True         | kalshi_brier_common_7d          |     23 |      0.028 |
|        3 |        0.200 | True         | polymarket_brier_common_7d      |     23 |      0.028 |
|        3 |        0.200 | True         | kalshi_brier_common_30d         |     20 |      0.157 |
|        3 |        0.200 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        7 |        0.050 | True         | kalshi_meeting_days             |     40 |   3583.000 |
|        7 |        0.050 | True         | polymarket_meeting_days         |     28 |   2659.000 |
|        7 |        0.050 | True         | zq_meeting_days                 |      5 |    754.000 |
|        7 |        0.050 | True         | kalshi_contract_days_usable     | 174460 |  94412.000 |
|        7 |        0.050 | True         | kalshi_vs_poly_mae_p_hold       |   1855 |      0.022 |
|        7 |        0.050 | True         | kalshi_vs_poly_mean_diff_p_hold |   1855 |     -0.005 |
|        7 |        0.050 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        7 |        0.050 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        7 |        0.050 | True         | kalshi_brier_common_7d          |     24 |      0.026 |
|        7 |        0.050 | True         | polymarket_brier_common_7d      |     24 |      0.027 |
|        7 |        0.050 | True         | kalshi_brier_common_30d         |     20 |      0.155 |
|        7 |        0.050 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        7 |        0.100 | True         | kalshi_meeting_days             |     40 |   5042.000 |
|        7 |        0.100 | True         | polymarket_meeting_days         |     28 |   2659.000 |
|        7 |        0.100 | True         | zq_meeting_days                 |      5 |    754.000 |
|        7 |        0.100 | True         | kalshi_contract_days_usable     | 174460 | 119705.000 |
|        7 |        0.100 | True         | kalshi_vs_poly_mae_p_hold       |   1983 |      0.022 |
|        7 |        0.100 | True         | kalshi_vs_poly_mean_diff_p_hold |   1983 |     -0.004 |
|        7 |        0.100 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        7 |        0.100 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        7 |        0.100 | True         | kalshi_brier_common_7d          |     24 |      0.026 |
|        7 |        0.100 | True         | polymarket_brier_common_7d      |     24 |      0.027 |
|        7 |        0.100 | True         | kalshi_brier_common_30d         |     20 |      0.156 |
|        7 |        0.100 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        7 |        0.200 | True         | kalshi_meeting_days             |     40 |   5149.000 |
|        7 |        0.200 | True         | polymarket_meeting_days         |     28 |   2659.000 |
|        7 |        0.200 | True         | zq_meeting_days                 |      5 |    754.000 |
|        7 |        0.200 | True         | kalshi_contract_days_usable     | 174460 | 122986.000 |
|        7 |        0.200 | True         | kalshi_vs_poly_mae_p_hold       |   1994 |      0.022 |
|        7 |        0.200 | True         | kalshi_vs_poly_mean_diff_p_hold |   1994 |     -0.004 |
|        7 |        0.200 | True         | kalshi_brier_common_1d          |     24 |      0.009 |
|        7 |        0.200 | True         | polymarket_brier_common_1d      |     24 |      0.007 |
|        7 |        0.200 | True         | kalshi_brier_common_7d          |     24 |      0.026 |
|        7 |        0.200 | True         | polymarket_brier_common_7d      |     24 |      0.027 |
|        7 |        0.200 | True         | kalshi_brier_common_30d         |     20 |      0.157 |
|        7 |        0.200 | True         | polymarket_brier_common_30d     |     20 |      0.152 |
|        3 |        0.100 | False        | kalshi_meeting_days             |     40 |   4397.000 |
|        3 |        0.100 | False        | polymarket_meeting_days         |     28 |   2621.000 |
|        3 |        0.100 | False        | zq_meeting_days                 |      5 |    754.000 |
|        3 |        0.100 | False        | kalshi_contract_days_usable     | 174460 | 100108.000 |
|        3 |        0.100 | False        | kalshi_vs_poly_mae_p_hold       |   1843 |      0.025 |
|        3 |        0.100 | False        | kalshi_vs_poly_mean_diff_p_hold |   1843 |     -0.012 |
|        3 |        0.100 | False        | kalshi_brier_common_1d          |     24 |      0.011 |
|        3 |        0.100 | False        | polymarket_brier_common_1d      |     24 |      0.007 |
|        3 |        0.100 | False        | kalshi_brier_common_7d          |     23 |      0.030 |
|        3 |        0.100 | False        | polymarket_brier_common_7d      |     23 |      0.028 |
|        3 |        0.100 | False        | kalshi_brier_common_30d         |     20 |      0.158 |
|        3 |        0.100 | False        | polymarket_brier_common_30d     |     20 |      0.152 |

## Gap Vs Cost

| h      |   days |   median_gap |   median_cost_lb |   share_gap_gt_cost |   share_gap_gt_cost_plus_2c |
|:-------|-------:|-------------:|-----------------:|--------------------:|----------------------------:|
| 1-7d   |    633 |        0.005 |            0.001 |               0.752 |                       0.021 |
| 8-30d  |   2119 |        0.005 |            0.007 |               0.641 |                       0.032 |
| 31-90d |   3427 |        0.009 |            0.012 |               0.450 |                       0.026 |
| >90d   |   2363 |        0.020 |            0.029 |               0.418 |                       0.138 |

## Mpt Path

|   window_rank |    days |   mean_diff_bps |   mae_bps |   corr |
|--------------:|--------:|----------------:|----------:|-------:|
|         1.000 | 241.000 |          -3.004 |     5.404 |  0.995 |
|         2.000 |  34.000 |          -0.237 |     7.646 |  0.960 |

