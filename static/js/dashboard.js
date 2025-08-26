document.getElementById('runLoadTest').addEventListener('click', async () => {
  await fetch('/admin/run-loadtest', { method: 'POST' });
  alert('Load test completed');
  loadLoadTests();
});

document.getElementById('runEval').addEventListener('click', async () => {
  await fetch('/admin/run-eval', { method: 'POST' });
  alert('Evaluation completed');
  loadExperiments();
});

async function loadExperiments() {
  const res = await fetch('/admin/api/experiments');
  const data = await res.json();
  const labels = data.map(d => d.file);
  const rouge = data.map(d => d.rougeL);

  new Chart(document.getElementById('experimentChart'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{ label: 'ROUGE-L', data: rouge }]
    }
  });
}

async function loadLoadTests() {
  const res = await fetch('/admin/api/loadtests');
  const data = await res.json();
  const labels = data.map(d => d.concurrency);
  const p95 = data.map(d => d.p95_ms);

  new Chart(document.getElementById('loadChart'), {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{ label: 'p95 (ms)', data: p95 }]
    }
  });
}

loadExperiments();
loadLoadTests();
