# Chapter 5: System Implementation, Testing and Evaluation

## 5.1 Introduction

This chapter explains how the electricity price forecasting system was implemented, tested and evaluated. The system predicted the difference between German and French day-ahead electricity prices, referred to as the price spread. It also monitored forecasting errors and compared three approaches to updating the forecasting model.

The main purpose was to investigate whether updating a model when its performance declined could maintain forecast accuracy while requiring fewer updates than a weekly schedule. The chapter describes the tools used, the preparation of the data, the forecasting process and the results. It also discusses the limitations of the study.

## 5.2 Implementation Environment

### 5.2.1 Hardware Environment

The system was developed and tested on an Apple Silicon computer running macOS. Historical experiments were run locally, so access to cloud services was not required to carry out the main research activities.

Table 5.1 identifies the hardware used for development.

**Table 5.1: Development hardware specifications**

| Component | Specification | Purpose |
| --- | --- | --- |
| Computer | Apple MacBook Pro | Local development and testing |
| Processor | Apple M1 Pro, 8-core CPU (6 performance and 2 efficiency cores) | Data preparation, model training and historical evaluation |
| Memory (RAM) | 32 GB unified memory | Working with datasets and running experiments |
| Storage | Internal Apple SSD, approximately 500 GB physical capacity | Storing source data, trained models and results |

### 5.2.2 Software Environment

Python was used because it supported the project's data preparation, machine learning and evaluation tasks within one environment. Table 5.2 lists the software versions installed in the local project environment on 6 November 2026.

**Table 5.2: Current local software versions and their roles (6 November 2026)**

| Software | Version or environment | Role in the project |
| --- | --- | --- |
| macOS | 26.6.2 (build 25G83) | Operating system for local development |
| Python | 3.14.4 | Implemented the forecasting workflow |
| Pandas | 3.0.3 | Organised and prepared tabular data |
| NumPy | 2.5.1 | Performed numerical calculations |
| scikit-learn | 1.9.0 | Supported model evaluation utilities |
| XGBoost | 3.3.0 | Predicted the electricity price spread |
| PyArrow | 25.0.0 | Read and wrote Parquet datasets and results |
| Matplotlib | 3.11.0 | Supported static charts |
| Plotly | 6.9.0 | Displayed interactive charts |
| PyYAML | 6.0.3 | Read experiment configuration files |
| Streamlit | 1.59.1 | Provided the review dashboard |
| watchdog | 6.0.0 | Supported dashboard file-change monitoring |
| pytest | 9.1.1 | Checked implemented functions |
| boto3 | 1.43.46 | Supported optional AWS integration |
| nbconvert | 7.17.1 | Supported notebook conversion and execution |
| ipykernel | 7.3.0 | Supported Python execution in notebooks |
| Git | 2.54.0 (Apple Git-157) | Supported source-code version control |
| uv | 0.11.11 | Managed the Python environment and dependencies |
| AWS services | Cloud services; no single software version applies | Supported the optional daily forecasting demonstration and online dashboard |

The table describes the current local environment; versions used in the historical experiment and cloud deployment may differ.

Experiment settings were stored separately from the program code. This allowed settings such as the training period and retraining threshold to be changed without rewriting the main functions. Data, trained models and results were also saved separately, making them easier to inspect and reuse.

### 5.2.3 Daily Forecasting and Dashboard

An optional cloud deployment was used to demonstrate daily forecasting. It ran the forecasting process on a schedule and saved the outputs for later review. The dashboard was started when needed rather than kept running continuously.

The dashboard displayed previously saved results. It did not start training or change the experiment when a user viewed a chart. This kept presentation separate from the research process and helped preserve the original results.

The daily process was scheduled for 18:15 Berlin time, while the forecasting setup used 18:00 as its reference time. This difference matters because information collected later should not automatically be treated as information available earlier. Further checks of source publication times are therefore needed.

The cloud demonstration showed that the components could work together. It did not establish long-term forecasting accuracy or prove that the system was ready for unrestricted public use.

> [Insert Figure 5.1: scheduled-run record and saved forecast summary, with execution date visible.]

**Figure 5.1: Scheduled forecasting execution and saved output for [verified run date].**

The dashboard provides a separate view of the saved outputs for review.

> [Insert Figure 5.2: dashboard screenshot showing the experiment, strategy and selected dates; identify historical or live results.]

**Figure 5.2: Dashboard view of [historical results or live forecasts] for [selected period].**

## 5.3 Dataset Description and Preparation

### 5.3.1 Data Sources and Coverage

Historical electricity prices were obtained from the SMARD platform operated by Germany's Federal Network Agency. The selected series covered the Germany/Luxembourg and French electricity markets, with ENTSO-E identified as the upstream source.

The forecasting target was calculated as:

\[
\text{Price spread} = \text{German price} - \text{French price}.
\]

A positive spread meant that the German price was higher than the French price. A negative spread meant that the French price was higher. Prices and forecasting errors were measured in euros per megawatt-hour (EUR/MWh).

**Table 5.3: Dataset summary**

| Item | Description |
| --- | --- |
| Historical price coverage | 2022–2025 |
| Paired hourly price records | 35,064 |
| Records available after preparing model inputs | 34,896 |
| Reported comparison period | 1 January 2023–31 December 2025 |
| Hourly forecasts per strategy | 26,304 |
| Delivery days compared | 1,096 |

The first 168 records were excluded from model-ready data because some inputs required earlier observations. Each strategy was evaluated over the same target hours, allowing their errors to be compared directly.

The saved experiment was labelled as a development comparison. The results are therefore reported as findings from model development rather than as performance on a completely untouched final test period.

### 5.3.2 Data Preparation

The preparation process checked the required columns, matched German and French observations by time and calculated the spread. Timestamps were stored consistently, while delivery dates were interpreted using Berlin time. This helped handle daylight-saving changes, when a delivery day can contain 23 or 25 hours instead of the usual 24.

Negative prices and unusually large price movements were retained. These can occur in electricity markets and should not be removed simply because they are extreme.

The model inputs described recent price behaviour, calendar patterns and expected generation. They included:

- Prices and spreads from 48 hours and one week earlier.
- Recent averages and measures of price variation, based on earlier observations.
- The hour, day of the week, month and whether the day was a weekend.
- German solar/wind and total-generation forecasts for the historical comparison.

These inputs gave the model information about past conditions and the delivery period. Nuclear availability was not included in the reported experiment, so its effect on accuracy was not measured.

To keep the historical experiment fair, observations were processed in time order. Inputs based on past prices used earlier observations, and retraining decisions used only errors considered available when the decision was made. This helped prevent data leakage, where information from the future incorrectly influences an earlier forecast. Automated tests checked these timing rules; limitations concerning original source publication times are discussed in Section 5.7.5.

> [Insert Figure 5.3: prepared-data sample showing timestamps, German and French prices, and calculated spreads, with timezone and units.]

**Figure 5.3: Sample of the prepared hourly price dataset, with prices and spreads in EUR/MWh.**

## 5.4 Model Training, Retraining and Evaluation

### 5.4.1 Forecasting Model

XGBoost was used to predict the price spread. It learns relationships between the supplied inputs and observed spreads. The same model type was used across all three strategies so that the study focused on when to update the model rather than on differences between forecasting algorithms.

Training and validation followed time order rather than randomly mixing earlier and later observations. Model versions and forecasts were saved so that results could be traced to the strategy that produced them.

> [Insert Figure 5.4: training-completion record and saved model identifier, labelled with the run date and whether it belongs to the historical comparison or a separate demonstration.]

**Figure 5.4: Completed XGBoost training and saved model record for [identified run].**

### 5.4.2 Retraining Strategies

Retraining means fitting the model again using more recent data. Table 5.4 summarises the three approaches.

**Table 5.4: Retraining strategies**

| Strategy | How it worked | Purpose |
| --- | --- | --- |
| No retraining | Trained once and kept the model unchanged | Provided a baseline for comparison |
| Fixed schedule | Updated the model weekly | Represented regular model maintenance |
| Performance triggered | Updated the model when recent forecasting error exceeded a set limit | Tested whether updates could respond to declining performance |

The performance-triggered approach monitored rolling RMSE: a measure of error calculated over a recent period. The currently retained settings use a seven-day monitoring period and a limit of 25 EUR/MWh. These settings still require confirmation against the original historical run.

An error-based rule does not necessarily produce fewer updates. If recent error stays above the limit, the rule may continue to request retraining. The evaluation therefore considered both forecast errors and the number of completed updates.

### 5.4.3 Evaluation Measures

Three main measures were used:

- **Root mean squared error (RMSE):** gives greater weight to large forecasting mistakes. A lower value is better.
- **Mean absolute error (MAE):** shows the average size of a forecasting mistake, regardless of whether the prediction was too high or too low. A lower value is better.
- **Retraining count:** records how often the model was updated after its initial training.

RMSE and MAE were reported in EUR/MWh. They were not percentages of predictions that were correct. Retraining counts indicated update activity, not directly measured computing costs or financial savings.

## 5.5 System Testing

### 5.5.1 Testing Approach

Automated tests checked individual functions and how different parts of the system worked together. Small datasets were used so that the main tests could run locally without cloud credentials or live data services.

The latest recorded full test run had **1,362 passing tests**, with **32 excluded from that run**. Separate focused runs recorded **62 passing dashboard tests** and **14 passing infrastructure tests**.

**Table 5.5: Selected test areas and outcomes**

| Area tested | Expected behaviour | Recorded outcome |
| --- | --- | --- |
| Local data loading | Load valid data without requiring cloud access | Relevant automated tests passed |
| Time-based inputs | Avoid using future observations in earlier forecasts | Timing and availability tests passed |
| Dashboard results | Read saved results without modifying the experiment | Dashboard tests passed |
| Missing results | Explain which required output was unavailable | Missing-file tests passed |
| Scheduled forecasting | Produce forecasts for all three strategies | The 4 November 2026 scheduled run produced 24 hourly forecasts per strategy for the following day |
| Incomplete inputs | Stop rather than issue forecasts with missing required data | An earlier manual attempt stopped because generation forecasts were incomplete |
| Dashboard recovery | Restart after a stability adjustment | Startup succeeded; repeated date-filter testing still needed to be recorded |

Passing these tests provided evidence that the checked functions behaved as intended. It did not prove that every possible failure had been eliminated. Formal user acceptance and accessibility testing were not completed.

> [Insert Figure 5.5: recorded full-test summary showing the command, execution date and actual passed/deselected totals.]

**Figure 5.5: Automated test summary for [recorded execution date].**

> [Insert Figure 5.6: actual error message for missing required input data or a results file, identifying the test condition.]

**Figure 5.6: System response to [specific missing input or results file].**

### 5.5.2 Problems Encountered

Deployment exposed several practical problems. Cloud resource limits required a smaller memory allocation, and the application package had to be rebuilt in a compatible format. Dashboard access was initially blocked by an incorrect network setup. Correcting the network allowed the page to load.

Historical results were also unavailable in the first cloud dashboard because the saved experiment files had not been made accessible there. Providing those files through cloud storage enabled the historical view to load without rerunning the experiment.

A later date-filter interaction caused the dashboard to stop. A memory-management setting was changed, after which the replacement dashboard started successfully. However, startup alone did not prove that the original interaction problem had been resolved. Repeated date changes still required documented retesting.

These experiences showed the importance of testing the deployed application as well as the underlying forecasting code.

## 5.6 Author Oversight and AI-Assisted Tools

AI assistance was used during programming, troubleshooting, analysis of saved results and drafting. This included OpenAI's GPT-6.1 Sol through OpenCode. The reported error measures were recalculated from the saved forecasts rather than accepted solely from generated explanations.

The student remains responsible for understanding the implementation, checking the evidence and references, and reviewing the final report. AI assistance does not replace independent evaluation or supervisor review.

## 5.7 Evaluation Results and Discussion

### 5.7.1 Forecast Accuracy

Table 5.6 presents the historical development results. Each strategy produced 26,304 hourly forecasts over the same 2023–2025 delivery period. The error measures were recalculated from the saved predictions and matched the stored summaries.

**Table 5.6: Forecast errors and retraining activity**

| Strategy | RMSE (EUR/MWh) | MAE (EUR/MWh) | Retrainings after initial training |
| --- | ---: | ---: | ---: |
| No retraining | 44.369 | 31.809 | 0 |
| Fixed schedule | 27.721 | **18.198** | 156 |
| Performance triggered | **27.498** | 18.205 | 509 |

Both retraining approaches had substantially lower errors than the unchanged model. Performance-triggered retraining reduced RMSE by approximately **38.02%** compared with no retraining. This suggests that updating the model was beneficial during the observed period.

The difference between the two retraining approaches was much smaller. Performance-triggered retraining had an RMSE about **0.80%** lower than weekly retraining, but weekly retraining had a slightly lower MAE. Neither approach was therefore better on every error measure. No statistical test was conducted to establish whether the small difference was meaningful beyond this experiment.

> [Insert Figure 5.7: actual and predicted spreads from the saved historical forecasts, using the same dates and scales for all strategies; identify units, timezone and interval-selection method.]

**Figure 5.7: Actual and predicted German–French electricity price spreads for [dates], historical development comparison.**

### 5.7.2 Performance Across Delivery Days

When errors were grouped by Berlin delivery date, performance-triggered retraining had lower daily RMSE than the unchanged model on **902 of 1,096 days (82.3%)**. This showed that its advantage over the static model occurred across many days rather than only a few isolated periods.

The figure does not mean that 82.3% of individual predictions were correct. It means that one strategy had a lower daily error than the other on that proportion of the observed delivery days.

Additional error checks showed that the unchanged model tended to predict spreads that were too low. Both retraining approaches reduced this tendency. Weekly retraining had a lower median absolute error, while performance-triggered retraining had a slightly lower 90th-percentile absolute error. These findings reinforce the conclusion that the two updating approaches had different strengths rather than one being consistently superior.

### 5.7.3 Retraining Activity

Performance-triggered retraining updated the model **509 times**, compared with **156 times** under the weekly schedule. It therefore retrained about **3.26 times as often**.

This result did not support the expectation that performance-triggered retraining would reduce update activity. It achieved a small RMSE advantage over weekly retraining, but required substantially more updates to do so.

The counts alone do not show which individual updates were unnecessary. They also do not measure the time, energy or money used by training. Nevertheless, they show that the tested setting did not meet the combined aim of maintaining accuracy while reducing retraining.

> [Insert Figure 5.8: full-period retraining-count bar chart, showing 0, 156 and 509 updates, with a zero-based axis and initial training excluded.]

**Figure 5.8: Retraining counts after initial training during the 2023–2025 historical development comparison.**

### 5.7.4 Assessment Against Project Goals

**Table 5.7: Summary of goal achievement**

| Project goal | Assessment |
| --- | --- |
| Build a forecasting workflow | Implemented, with data preparation, modelling and saved results |
| Compare three retraining approaches | Completed over a common historical development period |
| Limit the use of future information | Timing checks implemented; historical source availability remains a limitation |
| Maintain accuracy with fewer updates | Accuracy was comparable to weekly retraining, but fewer updates were not achieved |
| Demonstrate daily forecasting and result review | Demonstrated, but long-term live accuracy and reliability were not established |

### 5.7.5 Limitations

The findings should be interpreted within the following limits:

1. **The comparison formed part of development.** The reported years had already been inspected and cannot be presented as an untouched final test.
2. **Some experiment details still need confirmation.** The saved results cover 2023–2025, but the experiment file currently available specifies evaluation during 2024. The original settings and software versions must be confirmed before another researcher can repeat the comparison exactly. This gap concerns reproducing the experiment; the reported errors were checked against the saved predictions.
3. **Historical and live inputs differed.** The historical comparison used 18 inputs, while the daily deployment used 17. The total-generation forecast was omitted from the daily system because it was not consistently available; the solar/wind forecast was retained. The historical accuracy figures therefore cannot automatically be assigned to the deployed model. A matching evaluation using its exact inputs is needed.
4. **Information availability was not fully reconstructed.** Historical records may contain revisions, and successful data collection at 18:15 does not prove availability at the 18:00 reference time.
5. **Some possible improvements were not tested.** Nuclear availability was not included. It cannot be claimed to improve results without a controlled comparison.
6. **Broader validation remains limited.** Statistical significance, actual resource savings, long-term live performance and formal usability were not measured. Dashboard interaction stability still needed retesting, and wider access would require stronger security safeguards.

Overall, the project demonstrated a working research system and showed the value of updating the forecasting model compared with leaving it unchanged. However, the tested performance-triggered approach did not reduce retraining compared with a weekly schedule. This mixed result is central to the study's answer to its research question.
