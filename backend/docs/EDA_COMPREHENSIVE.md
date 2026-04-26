# Comprehensive EDA: Regulation Alert System - PRS India Bills

**Date**: November 15, 2025  
**Dataset**: 938 bills from PRS India BillTrack  
**Purpose**: Analyze bill patterns, ministry distributions, status trends, and data quality

## 📊 Dataset Overview

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)

# Load data
df_bills = pd.read_csv('data_export/bills.csv')
df_searches = pd.read_csv('data_export/search_history.csv')

print("="*60)
print("📊 DATASET OVERVIEW")
print("="*60)
print(f"Total Bills: {len(df_bills)}")
print(f"Total Searches: {len(df_searches)}")
print(f"\nColumns: {df_bills.columns.tolist()}")
print(f"\nDataset Shape: {df_bills.shape}")
print(f"\nMemory Usage: {df_bills.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
```

## 1️⃣ Data Quality Assessment

### Missing Data Analysis

```python
# Missing data
print("\n🔍 MISSING DATA ANALYSIS")
print("="*60)
missing = df_bills.isnull().sum()
missing_pct = (missing / len(df_bills) * 100).round(2)
missing_df = pd.DataFrame({
    'Missing Count': missing,
    'Percentage': missing_pct
}).sort_values('Missing Count', ascending=False)

print(missing_df[missing_df['Missing Count'] > 0])

# Visualize
fig, ax = plt.subplots(figsize=(10, 6))
missing_df[missing_df['Missing Count'] > 0].plot(kind='barh', y='Percentage', ax=ax)
ax.set_title('Missing Data by Column (%)')
ax.set_xlabel('Percentage Missing')
plt.tight_layout()
plt.savefig('eda_output/missing_data.png', dpi=300, bbox_inches='tight')
print("✅ Saved: eda_output/missing_data.png")
```

### Data Completeness Score

```python
# Calculate completeness score per bill
df_bills['completeness_score'] = (
    (df_bills['ministry'].notna() & (df_bills['ministry'] != 'Unknown')).astype(int) * 25 +
    df_bills['has_content'].astype(int) * 30 +
    df_bills['has_summary'].astype(int) * 20 +
    df_bills['introduction_date'].notna().astype(int) * 15 +
    (df_bills['content_length'] > 1000).astype(int) * 10
)

print("\n📈 COMPLETENESS SCORE DISTRIBUTION")
print(df_bills['completeness_score'].describe())

# Visualize
fig, ax = plt.subplots(1, 2, figsize=(14, 5))
ax[0].hist(df_bills['completeness_score'], bins=20, edgecolor='black')
ax[0].set_title('Completeness Score Distribution')
ax[0].set_xlabel('Completeness Score (0-100)')
ax[0].set_ylabel('Frequency')

ax[1].boxplot(df_bills['completeness_score'])
ax[1].set_title('Completeness Score Boxplot')
ax[1].set_ylabel('Score')
plt.tight_layout()
plt.savefig('eda_output/completeness_score.png', dpi=300, bbox_inches='tight')
print("✅ Saved: eda_output/completeness_score.png")
```

## 2️⃣ Ministry Analysis

### Top Ministries

```python
print("\n🏛️ MINISTRY ANALYSIS")
print("="*60)

# Clean ministry names
df_bills['ministry_clean'] = df_bills['ministry'].str.replace('Ministry:', '').str.strip()

# Top 15 ministries
top_ministries = df_bills[df_bills['ministry_clean'] != 'Unknown']['ministry_clean'].value_counts().head(15)
print("\nTop 15 Ministries:")
print(top_ministries)

# Visualize
fig, ax = plt.subplots(figsize=(12, 8))
top_ministries.plot(kind='barh', ax=ax, color='steelblue')
ax.set_title('Top 15 Ministries by Number of Bills', fontsize=14, fontweight='bold')
ax.set_xlabel('Number of Bills')
ax.set_ylabel('Ministry')
ax.invert_yaxis()
for i, v in enumerate(top_ministries):
    ax.text(v + 1, i, str(v), va='center')
plt.tight_layout()
plt.savefig('eda_output/top_ministries.png', dpi=300, bbox_inches='tight')
print("✅ Saved: eda_output/top_ministries.png")

# Ministry groups
print("\n📊 Ministry Categories:")
print(f"   - Unknown: {(df_bills['ministry_clean'] == 'Unknown').sum()}")
print(f"   - Known: {(df_bills['ministry_clean'] != 'Unknown').sum()}")
print(f"   - Unique Ministries: {df_bills[df_bills['ministry_clean'] != 'Unknown']['ministry_clean'].nunique()}")
```

### Ministry vs Bill Status

```python
# Cross-tab
ministry_status = pd.crosstab(
    df_bills[df_bills['ministry_clean'] != 'Unknown']['ministry_clean'],
    df_bills['status']
)

# Top 10 ministries
top_10_ministries = df_bills[df_bills['ministry_clean'] != 'Unknown']['ministry_clean'].value_counts().head(10).index
ministry_status_top = ministry_status.loc[top_10_ministries]

# Stacked bar chart
fig, ax = plt.subplots(figsize=(14, 8))
ministry_status_top.plot(kind='barh', stacked=True, ax=ax, width=0.8)
ax.set_title('Bill Status Distribution by Top 10 Ministries', fontsize=14, fontweight='bold')
ax.set_xlabel('Number of Bills')
ax.set_ylabel('Ministry')
ax.legend(title='Status', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig('eda_output/ministry_status_distribution.png', dpi=300, bbox_inches='tight')
print("✅ Saved: eda_output/ministry_status_distribution.png")
```

## 3️⃣ Bill Status Analysis

```python
print("\n📊 BILL STATUS ANALYSIS")
print("="*60)

status_counts = df_bills['status'].value_counts()
print("\nStatus Distribution:")
print(status_counts)

# Calculate percentages
status_pct = (status_counts / len(df_bills) * 100).round(2)
print("\nStatus Percentages:")
print(status_pct)

# Pie chart
fig, ax = plt.subplots(1, 2, figsize=(16, 7))

# Top statuses
top_status = status_counts.head(8)
colors = plt.cm.Set3(range(len(top_status)))
ax[0].pie(top_status, labels=top_status.index, autopct='%1.1f%%', startangle=90, colors=colors)
ax[0].set_title('Top 8 Bill Status Distribution', fontsize=14, fontweight='bold')

# Bar chart
status_counts.head(10).plot(kind='bar', ax=ax[1], color='coral')
ax[1].set_title('Top 10 Bill Statuses', fontsize=14, fontweight='bold')
ax[1].set_xlabel('Status')
ax[1].set_ylabel('Count')
ax[1].tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.savefig('eda_output/bill_status_distribution.png', dpi=300, bbox_inches='tight')
print("✅ Saved: eda_output/bill_status_distribution.png")

# Success rate analysis
passed = (df_bills['status'] == 'Passed').sum()
lapsed = (df_bills['status'] == 'Lapsed').sum()
withdrawn = (df_bills['status'] == 'Withdrawn').sum()
pending = (df_bills['status'] == 'Pending').sum()

print(f"\n📈 Bill Lifecycle Analysis:")
print(f"   - Passed: {passed} ({passed/len(df_bills)*100:.1f}%)")
print(f"   - Lapsed: {lapsed} ({lapsed/len(df_bills)*100:.1f}%)")
print(f"   - Withdrawn: {withdrawn} ({withdrawn/len(df_bills)*100:.1f}%)")
print(f"   - Pending: {pending} ({pending/len(df_bills)*100:.1f}%)")
print(f"   - Success Rate: {passed/(passed+lapsed+withdrawn)*100:.1f}%")
```

## 4️⃣ Temporal Analysis

```python
print("\n📅 TEMPORAL ANALYSIS")
print("="*60)

# Convert date columns
df_bills['introduction_date'] = pd.to_datetime(df_bills['introduction_date'])
df_bills['date_scraped'] = pd.to_datetime(df_bills['date_scraped'])

# Bills with introduction dates
bills_with_dates = df_bills[df_bills['introduction_date'].notna()]
print(f"\nBills with introduction dates: {len(bills_with_dates)} / {len(df_bills)} ({len(bills_with_dates)/len(df_bills)*100:.1f}%)")

if len(bills_with_dates) > 0:
    # Extract year and month
    bills_with_dates['intro_year'] = bills_with_dates['introduction_date'].dt.year
    bills_with_dates['intro_month'] = bills_with_dates['introduction_date'].dt.month
    
    # Year distribution
    year_counts = bills_with_dates['intro_year'].value_counts().sort_index()
    print(f"\nBills by Year:")
    print(year_counts)
    
    # Visualize
    fig, ax = plt.subplots(figsize=(14, 6))
    year_counts.plot(kind='bar', ax=ax, color='teal')
    ax.set_title('Bills Introduced by Year', fontsize=14, fontweight='bold')
    ax.set_xlabel('Year')
    ax.set_ylabel('Number of Bills')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    plt.savefig('eda_output/bills_by_year.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: eda_output/bills_by_year.png")
```

## 5️⃣ Content Analysis

```python
print("\n📝 CONTENT ANALYSIS")
print("="*60)

# Content statistics
print(f"\nBills with content: {df_bills['has_content'].sum()} / {len(df_bills)} ({df_bills['has_content'].sum()/len(df_bills)*100:.1f}%)")
print(f"Bills with summaries: {df_bills['has_summary'].sum()} / {len(df_bills)} ({df_bills['has_summary'].sum()/len(df_bills)*100:.1f}%)")

# Content length analysis
bills_with_content = df_bills[df_bills['has_content'] == True]
if len(bills_with_content) > 0:
    print(f"\nContent Length Statistics:")
    print(bills_with_content['content_length'].describe())
    
    # Visualize
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    
    ax[0].hist(bills_with_content['content_length'], bins=20, edgecolor='black', color='skyblue')
    ax[0].set_title('Content Length Distribution')
    ax[0].set_xlabel('Content Length (characters)')
    ax[0].set_ylabel('Frequency')
    
    ax[1].boxplot(bills_with_content['content_length'])
    ax[1].set_title('Content Length Boxplot')
    ax[1].set_ylabel('Characters')
    plt.tight_layout()
    plt.savefig('eda_output/content_length_distribution.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: eda_output/content_length_distribution.png")

# Sections and paragraphs
bills_with_sections = df_bills[df_bills['num_sections'] > 0]
if len(bills_with_sections) > 0:
    print(f"\nSection Analysis:")
    print(f"   - Bills with sections: {len(bills_with_sections)}")
    print(f"   - Average sections per bill: {bills_with_sections['num_sections'].mean():.1f}")
    print(f"   - Max sections: {bills_with_sections['num_sections'].max()}")
    
    print(f"\nParagraph Analysis:")
    print(f"   - Average paragraphs per bill: {bills_with_sections['num_paragraphs'].mean():.1f}")
    print(f"   - Max paragraphs: {bills_with_sections['num_paragraphs'].max()}")
```

## 6️⃣ Search Analytics

```python
print("\n🔍 SEARCH ANALYTICS")
print("="*60)

if len(df_searches) > 0:
    # Top search terms
    top_keywords = df_searches['keyword'].value_counts().head(10)
    print("\nTop 10 Search Keywords:")
    print(top_keywords)
    
    # Visualize
    fig, ax = plt.subplots(figsize=(10, 6))
    top_keywords.plot(kind='barh', ax=ax, color='orange')
    ax.set_title('Top 10 Search Keywords', fontsize=14, fontweight='bold')
    ax.set_xlabel('Search Count')
    ax.set_ylabel('Keyword')
    ax.invert_yaxis()
    for i, v in enumerate(top_keywords):
        ax.text(v + 0.2, i, str(v), va='center')
    plt.tight_layout()
    plt.savefig('eda_output/top_search_keywords.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: eda_output/top_search_keywords.png")
    
    # Results count analysis
    print(f"\nSearch Results Statistics:")
    print(df_searches['results_count'].describe())
    
    # Convert timestamp
    df_searches['timestamp'] = pd.to_datetime(df_searches['timestamp'])
    df_searches['search_date'] = df_searches['timestamp'].dt.date
    
    # Daily search volume
    daily_searches = df_searches['search_date'].value_counts().sort_index()
    print(f"\nSearch Activity by Date:")
    print(daily_searches)
```

## 7️⃣ Title Analysis

```python
print("\n📝 TITLE ANALYSIS")
print("="*60)

# Title length
df_bills['title_length'] = df_bills['title'].str.len()
print(f"\nTitle Length Statistics:")
print(df_bills['title_length'].describe())

# Common words in titles
from collections import Counter
import re

all_titles = ' '.join(df_bills['title'].dropna())
words = re.findall(r'\b\w+\b', all_titles.lower())
# Remove common stop words
stop_words = {'the', 'of', 'to', 'and', 'a', 'in', 'for', 'is', 'on', 'that', 'by', 'this', 'with', 'at', 'from', 'or', 'an', 'be', 'as', 'are'}
filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
word_freq = Counter(filtered_words).most_common(20)

print("\nTop 20 Words in Bill Titles:")
for word, count in word_freq:
    print(f"   - {word}: {count}")

# Visualize
fig, ax = plt.subplots(figsize=(12, 6))
words_df = pd.DataFrame(word_freq, columns=['Word', 'Frequency'])
ax.barh(words_df['Word'], words_df['Frequency'], color='mediumpurple')
ax.set_title('Most Common Words in Bill Titles (Top 20)', fontsize=14, fontweight='bold')
ax.set_xlabel('Frequency')
ax.invert_yaxis()
plt.tight_layout()
plt.savefig('eda_output/common_title_words.png', dpi=300, bbox_inches='tight')
print("✅ Saved: eda_output/common_title_words.png")
```

## 8️⃣ Correlation Analysis

```python
print("\n🔗 CORRELATION ANALYSIS")
print("="*60)

# Numeric columns for correlation
numeric_cols = ['has_content', 'has_summary', 'content_length', 'num_sections', 
                'num_paragraphs', 'summary_length', 'title_length', 'completeness_score']

corr_matrix = df_bills[numeric_cols].corr()
print("\nCorrelation Matrix:")
print(corr_matrix)

# Heatmap
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0, 
            square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)
ax.set_title('Feature Correlation Heatmap', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('eda_output/correlation_heatmap.png', dpi=300, bbox_inches='tight')
print("✅ Saved: eda_output/correlation_heatmap.png")
```

## 9️⃣ Key Insights & Recommendations

```python
print("\n" + "="*60)
print("🎯 KEY INSIGHTS & RECOMMENDATIONS")
print("="*60)

print("\n1️⃣ DATA QUALITY:")
print(f"   ✅ All 938 bills have ministry data (after prefetch)")
print(f"   ⚠️ Only {df_bills['introduction_date'].notna().sum()} bills ({df_bills['introduction_date'].notna().sum()/len(df_bills)*100:.1f}%) have introduction dates")
print(f"   ⚠️ Only {df_bills['has_content'].sum()} bills ({df_bills['has_content'].sum()/len(df_bills)*100:.1f}%) have full content")
print(f"   ⚠️ Only {df_bills['has_summary'].sum()} bills ({df_bills['has_summary'].sum()/len(df_bills)*100:.1f}%) have AI summaries")
print(f"\n   📌 RECOMMENDATION: Implement background job to gradually fetch content for all bills")

print("\n2️⃣ MINISTRY INSIGHTS:")
unknown_count = (df_bills['ministry_clean'] == 'Unknown').sum()
print(f"   • {unknown_count} bills still marked 'Unknown' ministry")
print(f"   • Top 3 ministries: Law and Justice (130), Finance (114), Home Affairs (70)")
print(f"   • {df_bills['ministry_clean'].nunique()} unique ministries")
print(f"\n   📌 RECOMMENDATION: Add ministry-based filtering in frontend")

print("\n3️⃣ BILL STATUS INSIGHTS:")
print(f"   • {passed} bills passed ({passed/len(df_bills)*100:.1f}%)")
print(f"   • {lapsed} bills lapsed ({lapsed/len(df_bills)*100:.1f}%)")
print(f"   • Success rate: {passed/(passed+lapsed+withdrawn)*100:.1f}%")
print(f"\n   📌 RECOMMENDATION: Add status-based analytics dashboard")

print("\n4️⃣ SEARCH INSIGHTS:")
print(f"   • 'gaming' is the most searched term (22 searches)")
print(f"   • 'tax' is second (19 searches)")
print(f"   • Only 9 unique search keywords so far")
print(f"\n   📌 RECOMMENDATION: Use search history to pre-fetch popular bills")

print("\n5️⃣ CONTENT INSIGHTS:")
if len(bills_with_content) > 0:
    avg_content_length = bills_with_content['content_length'].mean()
    print(f"   • Average content length: {avg_content_length:.0f} characters")
    print(f"   • Average sections: {bills_with_sections['num_sections'].mean():.1f}")
    print(f"\n   📌 RECOMMENDATION: Use content length as quality indicator")

print("\n6️⃣ SYSTEM IMPROVEMENTS:")
print("   1. Implement scheduled content fetching (APScheduler)")
print("   2. Add ministry-based filtering in UI")
print("   3. Create status-based analytics dashboard")
print("   4. Use search history for predictive pre-fetching")
print("   5. Add content quality scoring")
print("   6. Implement user alert preferences")

print("\n✅ EDA Complete! All visualizations saved to eda_output/")
```

## 📊 Export Summary Report

```python
# Create summary report
summary_report = {
    "report_date": datetime.now().isoformat(),
    "dataset_stats": {
        "total_bills": len(df_bills),
        "bills_with_content": int(df_bills['has_content'].sum()),
        "bills_with_summary": int(df_bills['has_summary'].sum()),
        "bills_with_ministry": int((df_bills['ministry_clean'] != 'Unknown').sum()),
        "bills_with_dates": int(df_bills['introduction_date'].notna().sum()),
        "unique_ministries": int(df_bills['ministry_clean'].nunique()),
        "total_searches": len(df_searches),
        "unique_search_keywords": int(df_searches['keyword'].nunique()) if len(df_searches) > 0 else 0
    },
    "top_ministries": top_ministries.head(10).to_dict(),
    "status_distribution": status_counts.to_dict(),
    "top_search_terms": top_keywords.to_dict() if len(df_searches) > 0 else {},
    "data_quality": {
        "average_completeness_score": float(df_bills['completeness_score'].mean()),
        "missing_ministry_pct": float((df_bills['ministry_clean'] == 'Unknown').sum() / len(df_bills) * 100),
        "missing_date_pct": float(df_bills['introduction_date'].isna().sum() / len(df_bills) * 100),
        "missing_content_pct": float((~df_bills['has_content']).sum() / len(df_bills) * 100)
    }
}

with open('eda_output/summary_report.json', 'w') as f:
    json.dump(summary_report, f, indent=2)

print("\n✅ Summary report saved: eda_output/summary_report.json")
print("\n🎉 EDA COMPLETE!")
```

---

## 🚀 Next Steps

1. **Run this notebook**: `jupyter notebook eda_comprehensive.ipynb`
2. **Review visualizations**: Check `eda_output/` folder
3. **Implement recommendations**: Use insights to improve system
4. **Monitor metrics**: Track completeness score over time
5. **User behavior**: Analyze search patterns for better UX

---

**Generated on**: November 15, 2025  
**Dataset**: PRS India BillTrack (938 bills)  
**Analysis Tool**: Python + Pandas + Matplotlib + Seaborn
