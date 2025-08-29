
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div class="toast-icon">
      ${type === 'success' ? '✓' : '⚠'}
    </div>
    <div class="toast-message">${message}</div>
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.classList.add('show');
  }, 100);
  
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      document.body.removeChild(toast);
    }, 300);
  }, 3000);
}


async function updateStats() {
  try {
   
    const loadTestsRes = await fetch('/admin/api/loadtests');
    const loadTests = await loadTestsRes.json();
    
   
    const experimentsRes = await fetch('/admin/api/experiments');
    const experiments = await experimentsRes.json();
    
   
    const totalTests = loadTests.length;
    const totalExperiments = experiments.length;
    
    const latestLoadTest = loadTests[0] || {};
    const latestExp = experiments[0] || {};
    

    if (document.getElementById('totalTests')) {
      document.getElementById('totalTests').textContent = totalTests;
    }
    
    if (document.getElementById('totalExperiments')) {
      document.getElementById('totalExperiments').textContent = totalExperiments;
    }
    
    if (document.getElementById('latestLatency') && latestLoadTest.p95_ms) {
      document.getElementById('latestLatency').textContent = `${latestLoadTest.p95_ms.toFixed(2)}ms`;
    }
    
    if (document.getElementById('latestRouge') && latestExp.rougeL) {
      document.getElementById('latestRouge').textContent = (latestExp.rougeL * 100).toFixed(1) + '%';
    }
  } catch (error) {
    console.error('Error updating stats:', error);
  }
}


document.getElementById('runLoadTest').addEventListener('click', async () => {
  const button = document.getElementById('runLoadTest');
  const originalText = button.textContent;
  const originalHTML = button.innerHTML;
  

  button.innerHTML = '<div class="loading"></div> Running Load Test...';
  button.disabled = true;
  
  try {
    const response = await fetch('/admin/run-loadtest', { method: 'POST' });
    
    if (response.ok) {
      showToast('Load test completed successfully', 'success');
      

      await Promise.all([loadLoadTests(), updateStats()]);
    } else {
      throw new Error('Load test failed');
    }
  } catch (error) {
    console.error('Load test error:', error);
    showToast('Load test failed. Please try again.', 'error');
  } finally {

    button.innerHTML = originalHTML;
    button.disabled = false;
  }
});


document.getElementById('runEval').addEventListener('click', async () => {
  const button = document.getElementById('runEval');
  const originalText = button.textContent;
  const originalHTML = button.innerHTML;
  
  button.innerHTML = '<div class="loading"></div> Running Evaluation...';
  button.disabled = true;
  
  try {
    const response = await fetch('/admin/run-eval', { method: 'POST' });
    
    if (response.ok) {
      showToast('Evaluation completed successfully', 'success');
      
     
      await Promise.all([loadExperiments(), updateStats()]);
    } else {
      throw new Error('Evaluation failed');
    }
  } catch (error) {
    console.error('Evaluation error:', error);
    showToast('Evaluation failed. Please try again.', 'error');
  } finally {

    button.innerHTML = originalHTML;
    button.disabled = false;
  }
});


async function loadExperiments() {
  try {
    const res = await fetch('/admin/api/experiments');
    const data = await res.json();
    
    if (data.length === 0) {
      document.getElementById('experimentChart').closest('.chart-card').innerHTML = `
        <h2><i class="fas fa-chart-bar"></i> Experiment Metrics</h2>
        <div class="no-data">No experiment data available. Run an evaluation to see metrics.</div>
      `;
      return;
    }
    
    const labels = data.map(d => d.file);
    const rouge = data.map(d => d.rougeL);
    const fkGrade = data.map(d => d.fk_grade);
    const latency = data.map(d => d.latency_s);
    

    if (window.experimentChart instanceof Chart) {
      window.experimentChart.destroy();
    }
    

    const ctx = document.getElementById('experimentChart').getContext('2d');
    window.experimentChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'ROUGE-L',
            data: rouge,
            backgroundColor: 'rgba(67, 97, 238, 0.7)',
            borderColor: 'rgba(67, 97, 238, 1)',
            borderWidth: 1
          },
          {
            label: 'Flesch-Kincaid Grade',
            data: fkGrade,
            backgroundColor: 'rgba(114, 9, 183, 0.7)',
            borderColor: 'rgba(114, 9, 183, 1)',
            borderWidth: 1,
            type: 'line',
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'ROUGE-L Score'
            }
          },
          y1: {
            position: 'right',
            beginAtZero: true,
            title: {
              display: true,
              text: 'Readability Grade'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        },
        plugins: {
          title: {
            display: true,
            text: 'Experiment Results'
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        }
      }
    });
  } catch (error) {
    console.error('Error loading experiments:', error);
    showToast('Failed to load experiment data', 'error');
  }
}

async function loadLoadTests() {
  try {
    const res = await fetch('/admin/api/loadtests');
    const data = await res.json();
    
    if (data.length === 0) {
      document.getElementById('loadChart').closest('.chart-card').innerHTML = `
        <h2><i class="fas fa-tachometer-alt"></i> Load Test p95 Latency</h2>
        <div class="no-data">No load test data available. Run a load test to see metrics.</div>
      `;
      return;
    }
    
    const labels = data.map(d => `${d.concurrency} users`);
    const p95 = data.map(d => d.p95_ms);
    const rps = data.map(d => d.rps);
    const errorRate = data.map(d => d.error_rate * 100);
    
 
    if (window.loadChart instanceof Chart) {
      window.loadChart.destroy();
    }
    

    const ctx = document.getElementById('loadChart').getContext('2d');
    window.loadChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'p95 Latency (ms)',
            data: p95,
            backgroundColor: 'rgba(247, 37, 133, 0.2)',
            borderColor: 'rgba(247, 37, 133, 1)',
            borderWidth: 2,
            tension: 0.3,
            yAxisID: 'y'
          },
          {
            label: 'Requests per Second',
            data: rps,
            backgroundColor: 'rgba(76, 201, 240, 0.2)',
            borderColor: 'rgba(76, 201, 240, 1)',
            borderWidth: 2,
            tension: 0.3,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Latency (ms)'
            }
          },
          y1: {
            position: 'right',
            beginAtZero: true,
            title: {
              display: true,
              text: 'RPS'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        },
        plugins: {
          title: {
            display: true,
            text: 'Load Test Performance'
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        }
      }
    });
  } catch (error) {
    console.error('Error loading load tests:', error);
    showToast('Failed to load load test data', 'error');
  }
}


document.addEventListener('DOMContentLoaded', function() {
  loadExperiments();
  loadLoadTests();
  updateStats();
  
 
  setInterval(() => {
    loadExperiments();
    loadLoadTests();
    updateStats();
  }, 60000);
});