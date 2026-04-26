"""
Quick EDA Script - Run all analyses at once
This is faster than running notebook cells one by one
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for faster execution
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import os
from collections import Counter
import re
import warnings
warnings.filterwarnings('ignore')

# Set visualization style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

# Create output directory
os.makedirs('eda_output', exist_ok=True)

print("="*70)
print("🚀 COMPREHENSIVE EDA: PRS India Bills")
print("="*70)

# Load data
print("\n📊 Loading data...")
df_bills = pd.read_csv('data_export/bills.csv')
df_searches = pd.read_csv('data_export/search_history.csv')
print(f"✅ Loaded {len(df_bills)} bills and {len(df_searches)} searches")

# Clean ministry names
df_bills['ministry_clean'] = df_bills['ministry'].fillna('Unknown').str.replace('Ministry:', '').str.strip()

# Calculate completeness score
df_bills['completeness_score'] = (
    (df_bills['ministry_clean'] != 'Unknown').astype(int) * 25 +
    df_bills['has_content'].astype(int) * 30 +
    df_bills['has_summary'].astype(int) * 20 +
    df_bills['introduction_date'].notna().astype(int) * 15 +
    (df_bills['content_length'] > 1000).astype(int) * 10
)

# Title length
df_bills['title_length'] = df_bills['title'].str.len()

print("\n" + "="*70)
print("📈 GENERATING VISUALIZATIONS")
print("="*70)

# 1. Missing Data Analysis
print("\n1️⃣ Missing Data Analysis...")
missing = df_bills.isnull().sum()
missing_pct = (missing / len(df_bills) * 100).round(2)
missing_df = pd.DataFrame({
    'Missing Count': missing,
    'Percentage (%)': missing_pct
}).sort_values('Missing Count', ascending=False)

fig, ax = plt.subplots(1, 2, figsize=(14, 5))
missing_df[missing_df['Missing Count'] > 0].plot(kind='barh', y='Percentage (%)', ax=ax[0], color='coral')
ax[0].set_title('Missing Data by Column (%)', fontsize=12, fontweight='bold')
ax[0].set_xlabel('Percentage Missing')
sns.heatmap(df_bills.isnull(), cbar=False, yticklabels=False, cmap='viridis', ax=ax[1])
ax[1].set_title('Missing Data Heatmap', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('eda_output/missing_data.png', dpi=300, bbox_inches='tight')
plt.close()
print("   ✅ Saved: missing_data.png")

# 2. Ministry Distribution
print("\n2️⃣ Ministry Distribution...")
top_ministries = df_bills[df_bills['ministry_clean'] != 'Unknown']['ministry_clean'].value_counts().head(15)
fig, ax = plt.subplots(figsize=(12, 8))
top_ministries.plot(kind='barh', ax=ax, color='steelblue')
ax.set_title('Top 15 Ministries by Number of Bills', fontsize=14, fontweight='bold')
ax.set_xlabel('Number of Bills', fontsize=12)
ax.set_ylabel('Ministry', fontsize=12)
ax.invert_yaxis()
for i, v in enumerate(top_ministries):
    ax.text(v + 1, i, str(v), va='center', fontsize=10)
plt.tight_layout()
plt.savefig('eda_output/top_ministries.png', dpi=300, bbox_inches='tight')
plt.close()
print("   ✅ Saved: top_ministries.png")

# 3. Bill Status Distribution
print("\n3️⃣ Bill Status Distribution...")
status_counts = df_bills['status'].value_counts()
passed = (df_bills['status'] == 'Passed').sum()
lapsed = (df_bills['status'] == 'Lapsed').sum()
withdrawn = (df_bills['status'] == 'Withdrawn').sum()
pending = (df_bills['status'] == 'Pending').sum()

fig, ax = plt.subplots(1, 2, figsize=(16, 6))
top_status = status_counts.head(8)
colors = plt.cm.Set3(range(len(top_status)))
ax[0].pie(top_status, labels=top_status.index, autopct='%1.1f%%', startangle=90, colors=colors)
ax[0].set_title('Top 8 Bill Status Distribution', fontsize=14, fontweight='bold')
status_counts.head(10).plot(kind='bar', ax=ax[1], color='coral')
ax[1].set_title('Top 10 Bill Statuses', fontsize=14, fontweight='bold')
ax[1].set_xlabel('Status', fontsize=12)
ax[1].set_ylabel('Count', fontsize=12)
ax[1].tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.savefig('eda_output/bill_status_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("   ✅ Saved: bill_status_distribution.png")

# 4. Ministry vs Status
print("\n4️⃣ Ministry vs Status Cross-Analysis...")
ministry_status = pd.crosstab(
    df_bills[df_bills['ministry_clean'] != 'Unknown']['ministry_clean'],
    df_bills['status']
)
top_10_ministries = df_bills[df_bills['ministry_clean'] != 'Unknown']['ministry_clean'].value_counts().head(10).index
ministry_status_top = ministry_status.loc[top_10_ministries]

fig, ax = plt.subplots(figsize=(14, 8))
ministry_status_top.plot(kind='barh', stacked=True, ax=ax, width=0.8, colormap='tab20')
ax.set_title('Bill Status Distribution by Top 10 Ministries', fontsize=14, fontweight='bold')
ax.set_xlabel('Number of Bills', fontsize=12)
ax.set_ylabel('Ministry', fontsize=12)
ax.legend(title='Status', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
plt.tight_layout()
plt.savefig('eda_output/ministry_status_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("   ✅ Saved: ministry_status_distribution.png")

# 5. Content Analysis (if content exists)
bills_with_content = df_bills[df_bills['has_content'] == True]
if len(bills_with_content) > 0:
    print(f"\n5️⃣ Content Analysis ({len(bills_with_content)} bills with content)...")
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ax[0].hist(bills_with_content['content_length'], bins=20, edgecolor='black', color='skyblue')
    ax[0].set_title('Content Length Distribution', fontsize=12, fontweight='bold')
    ax[0].set_xlabel('Content Length (characters)')
    ax[0].set_ylabel('Frequency')
    ax[0].axvline(bills_with_content['content_length'].mean(), color='red', linestyle='--', 
                  label=f'Mean: {bills_with_content["content_length"].mean():.0f}')
    ax[0].legend()
    ax[1].boxplot(bills_with_content['content_length'])
    ax[1].set_title('Content Length Boxplot', fontsize=12, fontweight='bold')
    ax[1].set_ylabel('Characters')
    plt.tight_layout()
    plt.savefig('eda_output/content_length_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: content_length_distribution.png")
else:
    print("\n5️⃣ Content Analysis... ⚠️ No content data yet")

# 6. Search Analytics (if searches exist)
if len(df_searches) > 0:
    print(f"\n6️⃣ Search Analytics ({len(df_searches)} searches)...")
    top_keywords = df_searches['keyword'].value_counts().head(10)
    fig, ax = plt.subplots(figsize=(10, 6))
    top_keywords.plot(kind='barh', ax=ax, color='orange')
    ax.set_title('Top 10 Search Keywords', fontsize=14, fontweight='bold')
    ax.set_xlabel('Search Count', fontsize=12)
    ax.set_ylabel('Keyword', fontsize=12)
    ax.invert_yaxis()
    for i, v in enumerate(top_keywords):
        ax.text(v + 0.3, i, str(v), va='center', fontsize=10)
    plt.tight_layout()
    plt.savefig('eda_output/top_search_keywords.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("   ✅ Saved: top_search_keywords.png")
else:
    print("\n6️⃣ Search Analytics... ⚠️ No search data yet")

# 7. Correlation Analysis
print("\n7️⃣ Correlation Analysis...")
numeric_cols = ['has_content', 'has_summary', 'content_length', 'num_sections', 
                'num_paragraphs', 'summary_length', 'title_length', 'completeness_score']
corr_matrix = df_bills[numeric_cols].corr()

fig, ax = plt.subplots(figsize=(11, 9))
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0, 
            square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax,
            vmin=-1, vmax=1)
ax.set_title('Feature Correlation Heatmap', fontsize=14, fontweight='bold', pad=20)
plt.xticks(rotation=45, ha='right')
plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig('eda_output/correlation_heatmap.png', dpi=300, bbox_inches='tight')
plt.close()
print("   ✅ Saved: correlation_heatmap.png")

# 8. Completeness Score
print("\n8️⃣ Completeness Score Distribution...")
fig, ax = plt.subplots(figsize=(10, 5))
df_bills['completeness_score'].hist(bins=20, edgecolor='black', color='mediumseagreen', ax=ax)
ax.set_title('Data Completeness Score Distribution', fontsize=14, fontweight='bold')
ax.set_xlabel('Completeness Score (0-100)', fontsize=12)
ax.set_ylabel('Frequency', fontsize=12)
ax.axvline(df_bills['completeness_score'].mean(), color='red', linestyle='--', 
           label=f'Mean: {df_bills["completeness_score"].mean():.1f}')
ax.legend()
plt.tight_layout()
plt.savefig('eda_output/completeness_score.png', dpi=300, bbox_inches='tight')
plt.close()
print("   ✅ Saved: completeness_score.png")

# Generate Summary Report
print("\n" + "="*70)
print("📊 KEY INSIGHTS")
print("="*70)

success_rate = passed/(passed+lapsed+withdrawn)*100 if (passed+lapsed+withdrawn) > 0 else 0

print(f"\n📋 Dataset Overview:")
print(f"   • Total bills: {len(df_bills)}")
print(f"   • Unique ministries: {df_bills['ministry_clean'].nunique()}")
print(f"   • Bills with content: {df_bills['has_content'].sum()} ({df_bills['has_content'].sum()/len(df_bills)*100:.1f}%)")
print(f"   • Bills with summaries: {df_bills['has_summary'].sum()} ({df_bills['has_summary'].sum()/len(df_bills)*100:.1f}%)")

print(f"\n🏛️ Top 3 Ministries:")
for i, (ministry, count) in enumerate(top_ministries.head(3).items(), 1):
    print(f"   {i}. {ministry}: {count} bills")

print(f"\n📊 Bill Status:")
print(f"   • Passed: {passed} ({passed/len(df_bills)*100:.1f}%)")
print(f"   • Lapsed: {lapsed} ({lapsed/len(df_bills)*100:.1f}%)")
print(f"   • Withdrawn: {withdrawn} ({withdrawn/len(df_bills)*100:.1f}%)")
print(f"   • Success Rate: {success_rate:.1f}%")

if len(df_searches) > 0:
    print(f"\n🔍 Search Analytics:")
    print(f"   • Total searches: {len(df_searches)}")
    print(f"   • Unique keywords: {df_searches['keyword'].nunique()}")
    print(f"   • Top search: '{df_searches['keyword'].value_counts().index[0]}' ({df_searches['keyword'].value_counts().iloc[0]} times)")

print(f"\n📈 Data Quality:")
print(f"   • Average completeness: {df_bills['completeness_score'].mean():.1f}/100")
print(f"   • Unknown ministries: {(df_bills['ministry_clean'] == 'Unknown').sum()}")
print(f"   • Missing dates: {df_bills['introduction_date'].isna().sum()} ({df_bills['introduction_date'].isna().sum()/len(df_bills)*100:.1f}%)")

# Save JSON summary
summary_report = {
    "report_date": datetime.now().isoformat(),
    "dataset_stats": {
        "total_bills": int(len(df_bills)),
        "bills_with_content": int(df_bills['has_content'].sum()),
        "bills_with_summary": int(df_bills['has_summary'].sum()),
        "bills_with_known_ministry": int((df_bills['ministry_clean'] != 'Unknown').sum()),
        "unique_ministries": int(df_bills['ministry_clean'].nunique()),
        "total_searches": int(len(df_searches)),
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
    },
    "bill_lifecycle": {
        "passed": int(passed),
        "lapsed": int(lapsed),
        "withdrawn": int(withdrawn),
        "pending": int(pending),
        "success_rate_pct": float(success_rate)
    }
}

with open('eda_output/summary_report.json', 'w', encoding='utf-8') as f:
    json.dump(summary_report, f, indent=2, ensure_ascii=False)

print("\n" + "="*70)
print("✅ EDA COMPLETE!")
print("="*70)
print("\n📁 Generated Files:")
print("   • eda_output/missing_data.png")
print("   • eda_output/top_ministries.png")
print("   • eda_output/bill_status_distribution.png")
print("   • eda_output/ministry_status_distribution.png")
print("   • eda_output/correlation_heatmap.png")
print("   • eda_output/completeness_score.png")
if len(bills_with_content) > 0:
    print("   • eda_output/content_length_distribution.png")
if len(df_searches) > 0:
    print("   • eda_output/top_search_keywords.png")
print("   • eda_output/summary_report.json")
print("\n🎉 All visualizations and insights ready!")
