# Experiment Report

## Verdict
- bio-inspired architecture is not consistently more stable than baseline.
- Strongest contributor in the ablation run: immune layer.
- Most conceptually attractive but comparatively modest in aggregate metrics: nervous layer.

## Aggregate Comparison
| scenario      | system   |   task_completion_rate_mean |   avg_latency_mean |   error_rate_mean |   recovery_time_after_failure_mean |   resource_efficiency_mean |   stability_score_mean |
|:--------------|:---------|----------------------------:|-------------------:|------------------:|-----------------------------------:|---------------------------:|-----------------------:|
| failure_storm | baseline |                       0.581 |              5.792 |             0.000 |                             10.000 |                      0.430 |                 20.878 |
| failure_storm | bio      |                       0.839 |              2.827 |             0.000 |                              6.000 |                      0.438 |                 15.116 |
| normal        | baseline |                       0.786 |              5.318 |             0.000 |                              9.500 |                      0.434 |                 20.127 |
| normal        | bio      |                       0.976 |              1.963 |             0.000 |                              3.750 |                      0.478 |                 15.733 |
| overload      | baseline |                       0.287 |              6.981 |             0.036 |                              0.000 |                      0.331 |                 17.624 |
| overload      | bio      |                       0.596 |              2.848 |             0.018 |                              0.000 |                      0.476 |                 16.734 |

## Bio vs Baseline Delta
| scenario      |   baseline |    bio | metric                      |   delta_bio_minus_baseline |
|:--------------|-----------:|-------:|:----------------------------|---------------------------:|
| failure_storm |      0.581 |  0.839 | task_completion_rate        |                      0.258 |
| normal        |      0.786 |  0.976 | task_completion_rate        |                      0.190 |
| overload      |      0.287 |  0.596 | task_completion_rate        |                      0.309 |
| failure_storm |      5.792 |  2.827 | avg_latency                 |                     -2.965 |
| normal        |      5.318 |  1.963 | avg_latency                 |                     -3.355 |
| overload      |      6.981 |  2.848 | avg_latency                 |                     -4.133 |
| failure_storm |      0.000 |  0.000 | error_rate                  |                      0.000 |
| normal        |      0.000 |  0.000 | error_rate                  |                      0.000 |
| overload      |      0.036 |  0.018 | error_rate                  |                     -0.018 |
| failure_storm |     10.000 |  6.000 | recovery_time_after_failure |                     -4.000 |
| normal        |      9.500 |  3.750 | recovery_time_after_failure |                     -5.750 |
| overload      |      0.000 |  0.000 | recovery_time_after_failure |                      0.000 |
| failure_storm |      0.430 |  0.438 | resource_efficiency         |                      0.008 |
| normal        |      0.434 |  0.478 | resource_efficiency         |                      0.045 |
| overload      |      0.331 |  0.476 | resource_efficiency         |                      0.145 |
| failure_storm |     20.878 | 15.116 | stability_score             |                     -5.763 |
| normal        |     20.127 | 15.733 | stability_score             |                     -4.394 |
| overload      |     17.624 | 16.734 | stability_score             |                     -0.890 |

## Layer Ablation
| scenario      | system       |   task_completion_rate_mean |   error_rate_mean |   recovery_time_after_failure_mean |   stability_score_mean |
|:--------------|:-------------|----------------------------:|------------------:|-----------------------------------:|-----------------------:|
| failure_storm | full_bio     |                       0.861 |             0.000 |                              5.128 |                 24.308 |
| failure_storm | no_endocrine |                       0.841 |             0.008 |                              6.428 |                 22.691 |
| failure_storm | no_immune    |                       0.757 |             0.000 |                              7.417 |                 22.094 |
| failure_storm | no_metabolic |                       0.794 |             0.000 |                              6.128 |                 22.288 |
| failure_storm | no_nervous   |                       0.867 |             0.000 |                              4.661 |                 21.721 |
| overload      | full_bio     |                       0.660 |             0.005 |                              9.333 |                 24.844 |
| overload      | no_endocrine |                       0.629 |             0.006 |                              9.250 |                 23.806 |
| overload      | no_immune    |                       0.508 |             0.000 |                             10.000 |                 21.671 |
| overload      | no_metabolic |                       0.552 |             0.000 |                             10.000 |                 23.983 |
| overload      | no_nervous   |                       0.629 |             0.000 |                              9.250 |                 21.427 |

## Layer Diagnostics
| scenario      | system   |   mean_endocrine_throttle_ratio_mean |   mean_immune_replacement_ratio_mean |   mean_metabolic_recovery_gain_mean |   mean_nervous_fast_lane_share_mean |
|:--------------|:---------|-------------------------------------:|-------------------------------------:|------------------------------------:|------------------------------------:|
| failure_storm | baseline |                                0.000 |                                0.000 |                               0.000 |                               0.000 |
| failure_storm | bio      |                                0.000 |                                0.100 |                               0.340 |                               0.201 |
| normal        | baseline |                                0.000 |                                0.000 |                               0.000 |                               0.000 |
| normal        | bio      |                                0.000 |                                0.100 |                               0.348 |                               0.167 |
| overload      | baseline |                                0.000 |                                0.000 |                               0.000 |                               0.000 |
| overload      | bio      |                                0.000 |                                0.100 |                               0.407 |                               0.195 |

## Acceptance Gates
| gate                                                   | status   |
|:-------------------------------------------------------|:---------|
| bio latency beats baseline in all scenarios            | PASS     |
| bio error beats baseline in all scenarios              | FAIL     |
| bio recovery beats baseline in failure_storm           | PASS     |
| full_bio beats no_endocrine on overload stability      | PASS     |
| full_bio beats no_endocrine on failure_storm stability | PASS     |

## Interpretation
- Nervous layer mainly improves urgent routing and local overload handling; its gain is visible but smaller when urgent traffic is not dominant.
- Immune layer matters most when repeated failures appear because isolation plus reserve substitution shortens recovery windows.
- Metabolic layer pays off over longer horizons by preventing low-energy collapse; without it, late-stage latency rises even if short-run throughput looks acceptable.
- Nervous layer is currently the weakest contributor in the ablation run, so its present implementation looks more like a partial idea than a finished resilience mechanism.