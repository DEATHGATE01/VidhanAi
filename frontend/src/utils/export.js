export const exportToCSV = (data, filename = 'export.csv') => {
  if (!data || data.length === 0) {
    alert('No data to export');
    return;
  }

  // Convert array of objects to CSV
  const headers = Object.keys(data[0]);
  const csvRows = [];

  // Add headers
  csvRows.push(headers.join(','));

  // Add data rows
  for (const row of data) {
    const values = headers.map(header => {
      const value = row[header];
      // Handle values with commas or quotes
      const escaped = ('' + value).replace(/"/g, '""');
      return `"${escaped}"`;
    });
    csvRows.push(values.join(','));
  }

  // Create blob and download
  const csvContent = csvRows.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export const exportBillsToCSV = (bills) => {
  const exportData = bills.map(bill => ({
    'Bill ID': bill.bill_id || '',
    'Title': bill.title || '',
    'Ministry': bill.ministry || '',
    'Status': bill.status || '',
    'Bill Type': bill.bill_type || '',
    'Introduction Date': bill.introduction_date || '',
    'Session': bill.session || '',
    'URL': bill.url || ''
  }));

  exportToCSV(exportData, `bills_export_${new Date().toISOString().split('T')[0]}.csv`);
};

export const exportSearchHistoryToCSV = (history) => {
  const exportData = history.map(item => ({
    'Date': new Date(item.timestamp).toLocaleString(),
    'Keyword': item.keyword,
    'Results Count': item.results_count,
    'User ID': item.user_id || 'Anonymous'
  }));

  exportToCSV(exportData, `search_history_${new Date().toISOString().split('T')[0]}.csv`);
};

export const exportTrendingToCSV = (trending) => {
  const exportData = trending.map(item => ({
    'Keyword': item.keyword,
    'Total Searches': item.search_count,
    'Unique Users': item.unique_users,
    'Last Searched': new Date(item.last_searched).toLocaleDateString()
  }));

  exportToCSV(exportData, `trending_searches_${new Date().toISOString().split('T')[0]}.csv`);
};
