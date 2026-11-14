# Chapter 6: Conclusions, Recommendations and Future Works

## 6.1 Introduction

This chapter presents the main conclusions of the electricity price spread forecasting project. It explains what was achieved, what the results mean for the research question and what should be improved. It also identifies areas for further research.

## 6.2 Conclusions

### 6.2.1 Implementation of the Forecasting System

The project developed a system for forecasting the difference between German and French day-ahead electricity prices. It brought together data preparation, model training, forecasting, error monitoring and result presentation. Saved forecasts and update records made it possible to examine how each retraining strategy performed.

The system could run locally, while an optional cloud deployment demonstrated scheduled forecasting and dashboard access. Automated tests supported the correctness of the functions tested. However, the original experiment settings and software environment still need to be brought together to make the reported historical comparison fully reproducible.

### 6.2.2 Forecast Accuracy

Both retraining approaches performed better than keeping the model unchanged during the reported development period. Performance-triggered retraining achieved an RMSE of **27.498 EUR/MWh**, compared with **27.721 EUR/MWh** for weekly retraining and **44.369 EUR/MWh** for no retraining.

The improvement over the unchanged model was substantial, with RMSE falling by approximately **38.02%**. However, the advantage over weekly retraining was small. Weekly retraining also had a slightly lower average absolute error. The findings therefore suggest similar overall accuracy between the two updating approaches, rather than clear superiority of performance-triggered retraining. The statistical significance of their difference was not established.

### 6.2.3 Answer to the Research Question

The study asked whether performance-triggered retraining could maintain forecast accuracy while reducing unnecessary updates compared with a fixed schedule.

The tested approach maintained accuracy comparable to weekly retraining, but it updated the model **509 times**, compared with **156 times** under the weekly schedule. The aim of reducing retraining was therefore **not achieved with the evaluated setting**.

This does not show that every performance-triggered approach will require more updates. It shows that the particular setting tested did not deliver both expected benefits. The result also highlights why forecast accuracy should be considered alongside update activity: a slightly lower error may come with substantially more retraining. The study did not determine whether individual updates were unnecessary or measure their actual cost.

### 6.2.4 Daily Operation and Review

The cloud demonstration showed that the system could run on a schedule and make saved results available through a dashboard. It did not establish reliable operation or accurate live forecasting over a long period.

The daily system also used one fewer input than the historical experiment. The historical accuracy results therefore cannot automatically be treated as the accuracy of the deployed model. In addition, repeated dashboard interactions still required documented retesting after a stability adjustment.

### 6.2.5 Overall Contribution

The main contribution was a working research system for comparing three retraining approaches using a common historical timeline. It showed that updating the model improved on leaving it unchanged, while revealing a trade-off between error reduction and update frequency.

The findings apply to the reported development comparison. They do not establish performance on an untouched final test, the benefit of nuclear availability data or readiness for commercial trading. The project should therefore be understood as a forecasting research prototype rather than a trading system.

## 6.3 Recommendations

### 6.3.1 Assess Accuracy and Update Frequency Together

Researchers should report forecast errors together with the number of model updates. For the evaluated setting, weekly retraining offered similar accuracy with substantially fewer updates. It is therefore a useful practical benchmark for further experiments. This does not establish monetary savings, since actual computing costs were not measured.

### 6.3.2 Complete the Experiment Record

The student should preserve the original data references, experiment settings, software versions, trained models and results together. The difference between the current configuration dates and the saved comparison period should be resolved before submission. This will help another researcher understand and repeat the work.

### 6.3.3 Keep Comparisons Fair

Further comparisons should use the same inputs, forecasting times and evaluation period for all three strategies. Information should only be used if it was available when the forecast would have been made.

The researcher and supervisor should also agree on the settings before a final evaluation. Previously inspected years should not be described as unseen test data. If no new evaluation period is available, further findings should be clearly labelled as exploratory.

### 6.3.4 Strengthen the Demonstration Before Wider Use

The developer should repeat dashboard date-selection tests and document the outcome. Access should remain restricted until reliability and security have been assessed more fully. The dashboard should continue to display saved results without changing experiments, and cloud resources should be stopped when not needed for review.

### 6.3.5 Make Results Easy to Interpret

Charts should clearly explain the price spread, error measures, units and comparison period. Historical experiments and live forecasts should be labelled separately. These improvements should preserve the original predictions and observations rather than alter the data to make performance appear better.

## 6.4 Future Works

### 6.4.1 Investigate Better Retraining Settings

Further work should test different error limits for triggering retraining. The purpose would be to find whether fewer updates can be achieved without an unacceptable loss of accuracy. Other experiment conditions should remain unchanged so that differences can be attributed to the retraining rule.

The study should also measure training time and resource use. This would provide stronger evidence about efficiency than counting updates alone. Any small accuracy advantage should be examined with suitable statistical analysis.

### 6.4.2 Investigate Nuclear Availability Data

Another possible extension is to include information about French nuclear availability or outages. Its usefulness should be tested rather than assumed.

A fair comparison would run the same experiment with and without the additional information. The data must represent what was known before forecasting, not later revised values. Only then could the study establish whether nuclear information improved accuracy or changed retraining needs.

### 6.4.3 Evaluate the Daily System Over a Longer Period

The historical comparison should first be repeated using the exact inputs of the deployed model. A longer live study could then compare issued forecasts with actual prices as they become available.

This would show how the system performs under practical conditions, including missing data, delayed publication and changing market conditions. It would also help distinguish a successful demonstration from dependable day-to-day operation.

### 6.4.4 Evaluate Dashboard Usability and Reliability

Future evaluation should involve representative users completing tasks such as comparing strategies, selecting dates and interpreting forecasting errors. Their difficulties and misunderstandings should be recorded rather than assuming that a working page is easy to use.

Longer interaction tests should also check whether the dashboard remains stable. These assessments would strengthen the review interface without changing the underlying forecasting evidence.
