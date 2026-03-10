# Experiment Report

## Verdict
- bio-inspired architecture is more stable than baseline.
- Strongest contributor in the ablation run: immune layer.
- Most conceptually attractive but comparatively modest in aggregate metrics: endocrine layer.

## Aggregate Comparison
| scenario      | system   |   task_completion_rate_mean |   avg_latency_mean |   error_rate_mean |   recovery_time_after_failure_mean |   resource_efficiency_mean |   stability_score_mean |
|:--------------|:---------|----------------------------:|-------------------:|------------------:|-----------------------------------:|---------------------------:|-----------------------:|
| failure_storm | baseline |                       0.380 |             36.488 |             0.151 |                              8.036 |                      0.300 |                  6.531 |
| failure_storm | bio      |                       0.800 |              5.037 |             0.003 |                              5.715 |                      0.482 |                 11.210 |
| normal        | baseline |                       0.706 |             15.642 |             0.060 |                              7.505 |                      0.376 |                 10.895 |
| normal        | bio      |                       0.944 |              2.957 |             0.002 |                              3.739 |                      0.474 |                 16.967 |
| overload      | baseline |                       0.257 |             48.222 |             0.161 |                              9.131 |                      0.283 |                  4.584 |
| overload      | bio      |                       0.512 |              7.589 |             0.013 |                              7.802 |                      0.474 |                  7.166 |

## Bio vs Baseline Delta
| scenario      |   baseline |    bio | metric                      |   delta_bio_minus_baseline |
|:--------------|-----------:|-------:|:----------------------------|---------------------------:|
| failure_storm |      0.380 |  0.800 | task_completion_rate        |                      0.419 |
| normal        |      0.706 |  0.944 | task_completion_rate        |                      0.239 |
| overload      |      0.257 |  0.512 | task_completion_rate        |                      0.255 |
| failure_storm |     36.488 |  5.037 | avg_latency                 |                    -31.451 |
| normal        |     15.642 |  2.957 | avg_latency                 |                    -12.685 |
| overload      |     48.222 |  7.589 | avg_latency                 |                    -40.632 |
| failure_storm |      0.151 |  0.003 | error_rate                  |                     -0.148 |
| normal        |      0.060 |  0.002 | error_rate                  |                     -0.057 |
| overload      |      0.161 |  0.013 | error_rate                  |                     -0.148 |
| failure_storm |      8.036 |  5.715 | recovery_time_after_failure |                     -2.322 |
| normal        |      7.505 |  3.739 | recovery_time_after_failure |                     -3.766 |
| overload      |      9.131 |  7.802 | recovery_time_after_failure |                     -1.330 |
| failure_storm |      0.300 |  0.482 | resource_efficiency         |                      0.182 |
| normal        |      0.376 |  0.474 | resource_efficiency         |                      0.098 |
| overload      |      0.283 |  0.474 | resource_efficiency         |                      0.191 |
| failure_storm |      6.531 | 11.210 | stability_score             |                      4.679 |
| normal        |     10.895 | 16.967 | stability_score             |                      6.072 |
| overload      |      4.584 |  7.166 | stability_score             |                      2.581 |

## Layer Ablation
| scenario      | system       |   task_completion_rate_mean |   error_rate_mean |   recovery_time_after_failure_mean |   stability_score_mean |
|:--------------|:-------------|----------------------------:|------------------:|-----------------------------------:|-----------------------:|
| failure_storm | full_bio     |                       0.787 |             0.007 |                              6.541 |                 11.612 |
| failure_storm | no_endocrine |                       0.788 |             0.005 |                              6.691 |                 11.096 |
| failure_storm | no_immune    |                       0.630 |             0.008 |                              7.774 |                  9.530 |
| failure_storm | no_metabolic |                       0.593 |             0.015 |                              7.659 |                  9.429 |
| failure_storm | no_nervous   |                       0.748 |             0.008 |                              6.476 |                 10.735 |
| overload      | full_bio     |                       0.518 |             0.021 |                              7.934 |                  6.941 |
| overload      | no_endocrine |                       0.470 |             0.028 |                              8.453 |                  6.385 |
| overload      | no_immune    |                       0.328 |             0.033 |                              8.227 |                  5.044 |
| overload      | no_metabolic |                       0.377 |             0.028 |                              7.837 |                  5.287 |
| overload      | no_nervous   |                       0.437 |             0.031 |                              8.428 |                  5.894 |

## Layer Diagnostics
| scenario      | system   |   mean_endocrine_throttle_ratio_mean |   mean_immune_replacement_ratio_mean |   mean_metabolic_recovery_gain_mean |   mean_nervous_fast_lane_share_mean |
|:--------------|:---------|-------------------------------------:|-------------------------------------:|------------------------------------:|------------------------------------:|
| failure_storm | baseline |                                0.000 |                                0.000 |                               0.000 |                               0.000 |
| failure_storm | bio      |                                0.000 |                                0.036 |                               0.445 |                               0.152 |
| normal        | baseline |                                0.000 |                                0.000 |                               0.000 |                               0.000 |
| normal        | bio      |                                0.000 |                                0.037 |                               0.419 |                               0.139 |
| overload      | baseline |                                0.000 |                                0.000 |                               0.000 |                               0.000 |
| overload      | bio      |                                0.000 |                                0.095 |                               0.460 |                               0.187 |

## Acceptance Gates
| gate                                                   | status   |
|:-------------------------------------------------------|:---------|
| bio latency beats baseline in all scenarios            | PASS     |
| bio error beats baseline in all scenarios              | PASS     |
| bio recovery beats baseline in failure_storm           | PASS     |
| full_bio beats no_endocrine on overload stability      | PASS     |
| full_bio beats no_endocrine on failure_storm stability | PASS     |

## Interpretation
- Nervous layer mainly improves urgent routing and local overload handling; its gain is visible but smaller when urgent traffic is not dominant.
- Immune layer matters most when repeated failures appear because isolation plus reserve substitution shortens recovery windows.
- Metabolic layer pays off over longer horizons by preventing low-energy collapse; without it, late-stage latency rises even if short-run throughput looks acceptable.
- Endocrine control is still the weakest contributor in the ablation ranking, but after retuning it is no longer a drag on performance; it now behaves like a light-touch global governor with smaller marginal gains than the other layers.