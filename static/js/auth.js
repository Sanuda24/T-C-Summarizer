// dropdown
document.addEventListener('DOMContentLoaded', function() {
  const btn = document.getElementById('profileBtn');
  const menu = document.getElementById('dropdownMenu');
  
  if (btn && menu) {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      menu.classList.toggle('show');
    });
    
    document.addEventListener('click', (e) => {
      if (!menu.contains(e.target) && e.target !== btn) {
        menu.classList.remove('show');
      }
    });
  }
});

// simple password validation
function passesRule(pw) {
  if (typeof pw !== 'string') return false;
  if (pw.length < 6) return false;
  if (!/[A-Za-z]/.test(pw)) return false;
  if (!/\d/.test(pw)) return false;
  return true;
}

document.addEventListener('DOMContentLoaded', function() {
  const signupForm = document.getElementById('signupForm');
  if (signupForm) {
    signupForm.addEventListener('submit', (e) => {
      const pw = signupForm.querySelector('input[name="password"]').value || '';
      if (!passesRule(pw)) {
        e.preventDefault();
        alert('Password must be at least 6 characters and include letters & numbers.');
      }
    });
  }

  const changePwForm = document.getElementById('changePasswordForm');
  if (changePwForm) {
    changePwForm.addEventListener('submit', (e) => {
      const pw = changePwForm.querySelector('input[name="new_password"]').value || '';
      if (!passesRule(pw)) {
        e.preventDefault();
        alert('New password must be at least 6 characters and include letters & numbers.');
      }
    });
  }
});