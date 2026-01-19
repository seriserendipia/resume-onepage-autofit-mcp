
content = r"""# YIHE (MARY) LU
Los Angeles, CA (Willing to relocate) | (213) 301-2014 | yihelu@usc.edu | [linkedin.com/in/yihe-lu/](https://linkedin.com/in/yihe-lu/) | [github.com/seriserendipia](https://github.com/seriserendipia)

---

## EDUCATION

**University of Southern California** · Los Angeles, CA  
*Master of Science in Analytics (GPA: 3.85/4.0)*  
*August 2024 - Present*  
- **Relevant Coursework:** ISE 534 Data Analytics Consulting, ISE 529 Predictive Analytics, ISE 547 Applied Generative Artificial Intelligence for Enterprises, CSCI 566 Deep Learning and Its Applications, ISE 530 Optimization Methods for Analytics, ISE 558 Data Management for Analytics, CSCI 644 Natural Language Dialogue Systems
- **Activities:** Kortschak Center for Learning and Creativity, Viterbi Impact, University Chorus

**Shanghai Lixin University** · Shanghai, China  
*Bachelor of Science in Data Science and Big Data Technology (GPA: 3.6/4, Top student scholar)*  
*September 2020 - June 2024*  
- **Relevant Coursework:** Python Data Analysis, Business Intelligence Application, Machine Learning and Data Mining, Hadoop Ecosystem
- **Activities:** Academic Development Center, Debate Team 

---

## INTERNSHIP EXPERIENCE

**International Vitamin Co.** · Shanghai, China  
*Data Analyst Intern*  
*March 2024 - July 2024*  
- Integrated global corporate strategy across 4 factories and 3 warehouses between China and the US, facilitating communication and strategy localization.
- Designed a purchase order delay tracking dashboard by integrating internal databases and external APIs. The tracking system increased the overall on-time rate by 5% and decreased average delay time by 1-2 weeks, improving on-time delivery rates for Walmart from 85% to 97%.
- Conducted spend and market analysis to optimize the procurement portfolio, determined price influencing factors, and supported procurement negotiations, projecting a 10% cost reduction.
- Automated daily KPI reports with Python scripts, reducing manual reporting time by 15 hours/week.

**Hitachi (China) Co., Ltd.** · Shanghai, China  
*Data Analyst Intern*  
*September 2022 - February 2023*  
- Processed and analyzed 1.89 million after-sales maintenance records using process mining to extract insights. Visualized and identified bottlenecks in inventory reconciliation and 7 other key performance indicators, reducing order fulfillment delays by 20%.
- Implemented a customized genetic algorithm to optimize maintenance engineer scheduling, reducing labor costs by 8%.

---

## SKILLS

- **Programming Languages:** Python, SQL (PostgreSQL, MySQL), Scala
- **Analysis Tools:** Hive, Snowflake, BigQuery, Pandas, Scikit-Learn, ETL Pipelines, Docker, PyTorch, Spark, PySpark, Hadoop, HiveQL, Git, Linux
- **Languages:** English (Professional), Chinese (Native), Japanese (Professional, JLPT N1 certificate)

---

## PROJECTS

**Comprehensive Evaluation Framework for LLM Commonsense Reasoning** | *Python, Asyncio, Tenacity, OpenRouter API, Prompt Engineering*  
*Oct 2025 – Oct 2025 (Independent Developer)*  
- Independently designed and engineered a high-performance framework to evaluate state-of-the-art LLMs (GPT-OSS, Gemini 2.0, Qwen 2.5) on five major commonsense reasoning benchmarks (CommonsenseQA, HellaSwag, PIQA, SocialIQA, TG-CSR). Processed over 30,000+ inference requests.
- **High-Throughput Async Architecture:** Developed a fully asynchronous evaluation pipeline using asyncio, enabling the full-scale evaluation of 15,000+ validation samples per experiment run with high concurrency. Implemented robust error handling using tenacity with exponential backoff.
- **Advanced Robustness Analysis & Insights:**
  - **Uncertainty Calibration ("I don't know" Test):** Discovered that Gemini 2.0 exhibits the most honest behavior, prioritizing caution over blind guessing, whereas other models displayed overconfidence.
  - **Semantic Stability:** Engineered an automated paraphrasing pipeline for PIQA; analysis revealed Qwen-2.5 achieved the highest consistency (94%).
  - **Distractor Analysis:** Quantified the impact of distractor options, demonstrating that reducing choice complexity consistently improves performance.
- **System Optimization:** Built a modular data loading system with built-in checkpointing and caching mechanisms, optimizing API costs.

**Multi-Modal Intelligent RAG System** | *Python, LangChain, FAISS, PyTorch, CLIP, DeepSeek OCR, Ragas*  
*September 2025 - November 2025*  
- Developed a Retrieval-Augmented Generation system capable of processing multimodal academic and business documents.
- **Multi-Modal Retrieval Architecture:** Architected a dual-channel retrieval system using OpenAI CLIP and FAISS to index both text and images. Leveraged Qwen3-Embedding to achieve a stable Top-5 Retrieval Recall of over 85%.
- **Unstructured Data Governance:** Integrated DeepSeek OCR engine to process PDFs containing complex charts and formulas, achieving 98% text extraction accuracy.
- **Data-Driven Evaluation Loop:** Built an automated testing pipeline using Ragas to monitor key metrics like Answer Relevancy and Context Precision. Utilized quantitative feedback to refine chunking strategies, improving overall response quality scores by 30%.

**Optimizing Math Reasoning in Small LLMs via CoT-SFT-GRPO** | *PyTorch, Hugging Face (Transformers, TRL, PEFT), GRPO, LoRA, Multi-GPU Training*  
*September 2025 - December 2025*  
- **Pipeline Design:** Developed a robust two-stage post-training pipeline (SFT + RL) for Qwen2.5-1.5B to enhance mathematical reasoning, addressing the instability issues of training RL from scratch.
- **SFT & Verification:** Implemented Supervised Fine-Tuning with Chain-of-Thought data as a warm-up phase. Conducted ablation studies verifying that SFT initialization is critical for constraining the policy search space.
- **RL Optimization (GRPO):** Applied Group Relative Policy Optimization to align the model with logical correctness rewards without requiring a Value Model.
- **Results:** Achieved 68.47% accuracy on GSM8K, outperforming the baseline by ~12% and the SFT-only model by ~7%, while demonstrating superior generalization on OOD tasks (ARC-Challenge).
- Link: https://github.com/seriserendipia/COT-SFT-LLM-MATH

**AI Agent Job Application Assistant (Full-Stack Chrome Extension)** | *AI Agent, JavaScript, Python, Flask, Chrome Extension APIs, OpenAI GPT, Google OAuth 2.0, MCP Protocol*  
- Architected and led a team of 5 to develop a Full-Stack AI Agent System (Chrome Extension + Python Flask backend) that automates personalized outreach.
- Integrated GPT and multi-agent interaction framework to create intelligent email generation and send-out workflow through multi-turn conversation, matching user resumes with job descriptions.
- **Backend Services:** Designed RESTful APIs with Flask, implemented a Model Context Protocol (MCP) server for automated Gmail sending, and built Google OAuth 2.0 integration for seamless user authentication.

**Mortality Prediction in Sepsis-Associated ARDS** | *Python, LightGBM, XGBoost, SHAP, ADASYN, MIMIC-III*  
*Jan 2025 - May 2025*  
- **Pipeline Development:** Developed an end-to-end ML pipeline to predict mortality for 2,583 patients using the **MIMIC-III v1.4** database. Extracted 55 clinical features including vital signs and lab results.
- **Feature Engineering & Balancing:** Engineered a robust feature selection algorithm and addressed class imbalance (31.6% mortality) using **ADASYN** to synthesize minority samples.
- **Model Optimization:** Evaluated 8 models using 5-fold cross-validation; achieved state-of-the-art performance with **LightGBM** (AUC: 0.88, Accuracy: 0.81).
- **Interpretability:** Leveraged **SHAP** to identify top predictors like **SAPS II** and **Lactate**.
- **Version Control:** Managed code iterations and collaborative modules using **Git**.

**Los Angeles Airbnb Price Prediction Analysis** | *Python, CatBoost, Scikit-learn, Seaborn, Plotly, Pandas*  
*Feb 2025 - Feb 2025*  
- **High-Cardinality Handling:** Optimized categorical encoding for variables like `neighborhood` and `property_type` by analyzing training set distributions; merged rare categories into "Other" to prevent overfitting.
- **Statistical Modeling:** Applied **log transformation** to the target price variable to mitigate skewness. Extracted text-based features (description word counts) to capture perceived listing quality.
- **Performance Tuning:** Conducted hyperparameter tuning for **CatBoost**, reaching an **R² of 0.81** and **RMSE of 0.3845** through 5-fold cross-validation.
- **Visualization:** Developed interactive dashboards using **Plotly** and **Seaborn** to visualize feature correlations and price distribution across LA neighborhoods.

**Campus Consumption Behavior Analysis & Decision Support System** | *Python, Pandas, Scikit-learn, K-Means, PCA*  
*Feb 2023 - Apr 2023*  
- **Large-scale Data ETL:** Integrated and processed 520,000+ campus smart card transaction and access control records. Optimized data quality by implementing a custom time-window algorithm to merge multiple transactions occurring within 3 minutes at the same location.
- **Advanced Feature Engineering:** Extracted 15+ behavioral features, including total consumption, frequency, standard deviation of spending, and meal-specific habits. Applied PCA for dimensionality reduction.
- **User Segmentation Modeling:** Developed a K-Means clustering model to categorize the student body into 5 distinct groups (e.g., "High-frequency Spenders," "Economical Consumers").
- **Actionable Business Insights:** Conducted temporal analysis of weekday vs. weekend dining peaks to provide staffing and inventory recommendations for campus canteens.
- **Financial Aid Policy Support:** Analyzed low-consumption student groups and proposed a data-driven evaluation framework for financial aid eligibility based on "Average Transaction Value" and "Consumption Frequency".

**Customer Journey Analytics for Guangdong Broadcast Group**  
*November 2020 - May 2021*  
- Built a survival analysis model to predict customer churn for the SaaS platform of GuangDong Broadcast Group using product usage data (10M+ user events). Built PySpark ETL pipelines. Identified key drop-off points in the user journey, leading to a 11% reduction in churn via targeted discount campaigns.
- Developed a dynamic segmentation system using DBSCAN clustering and RFM analysis to categorize users into personas. Insights informed feature prioritization, increasing feature adoption by 15%.

**Shanghai Lixin University - Finance Analytics Student Assistant Researcher** · Shanghai, China  
*November 2023 - February 2024*  
- Research on sentiment analysis of listed companies' annual reports; the sentiment analysis factor improved prediction accuracy by 8.3%.
- Constructed a diversified portfolio of major asset classes using a neural network signal and the Black-Litterman model. Outperformed the benchmark index by 15% in a one-year backtest.

**WAKEUP — An Assistant APP for Efficiency Analysis**  
*November 2020 - May 2021*  
- Implemented machine learning algorithms to calculate concentration efficiency scores from movement and sound sensor data.
- Achieved the 3rd Prize in the Shanghai College Students' Computer Application Skills Competition.

---

## VOLUNTEER AND COMMUNITY INVOLVEMENT

**USC Kortschak Center for Learning and Creativity (KCLC)** · Part-time Student Worker · *Jun 2025 - Present*  
- Spearheaded over 10 outreach tabling events in summer semester, effectively pitching KCLC to 200+ students, significantly boosting program visibility.
- Managed phone calls and emails, and provided assistance to walk-in and appointment-based students.

**Viterbi Impact Volunteer** · *Sep 2024 - Present*  
- **Hustle N' Code Hackathon – Developer Volunteer:** Mentored and guided a group of 4 girls (ages 8-13) in building their first website aimed at distributing free food information. Assisted with troubleshooting technical issues.
- **LA Maker Faire – Volunteer:** Guided over 30 children in soldering, helping them assemble circuit boards and LED lights. Soldered more than 50 circuit boards used as educational tools.
- **Food Forward – Volunteer:** Participated in an orange harvesting event at The Huntington, collecting and boxing fresh produce.
- **Beanies for Preemies – Volunteer:** Hand-knitted beanies for premature babies in Los Angeles County to help them maintain body temperature.

**Lixin Academic Development Center** · Japanese Language Instructor · *Sep 2021 - Dec 2022*  
- Taught free evening Japanese language courses for 3 consecutive semesters, enrolling over 200 students.
- Developed course content, instructional materials, slides, videos, and an interactive quiz application.
- Utilized data visualization tools to track and analyze attendance rates, optimizing course engagement.
- Achieved the highest attendance rate among 12 courses, being awarded “Best Instructor”.

---
"""

with open(r'd:\PythonEx\VirtualJobSeekerAgent\myresumebuilder\myexperience.md', 'w', encoding='utf-8') as f:
    f.write(content)
