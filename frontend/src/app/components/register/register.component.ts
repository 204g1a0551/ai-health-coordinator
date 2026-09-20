import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrl: './register.component.css',
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);

  registerForm: FormGroup = this.fb.group(
    {
      fullName: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(20)]],
      dob: [''],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]],
    },
    { validators: this.passwordMatchValidator }
  );

  showPassword = false;
  showConfirmPassword = false;
  isLoading = false;
  errorMessage = '';
  successMessage = '';

  passwordMatchValidator(g: FormGroup) {
    const pwd = g.get('password')?.value;
    const confirm = g.get('confirmPassword')?.value;
    return pwd === confirm ? null : { mismatch: true };
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPasswordVisibility(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  // Password strength calculation
  get passwordStrength(): { score: number; label: string; color: string } {
    const pwd = this.registerForm.get('password')?.value || '';
    if (!pwd) {
      return { score: 0, label: '', color: '#e2e8f0' };
    }

    let score = 0;
    if (pwd.length >= 8) score += 1;
    if (pwd.length >= 12) score += 1;
    if (/[A-Z]/.test(pwd)) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1;

    if (score <= 1) {
      return { score: 25, label: 'Weak', color: '#ef4444' };
    } else if (score === 2) {
      return { score: 50, label: 'Fair', color: '#f59e0b' };
    } else if (score === 3 || score === 4) {
      return { score: 75, label: 'Strong', color: '#0ea5e9' };
    } else {
      return { score: 100, label: 'Very Strong', color: '#10b981' };
    }
  }

  onSubmit(): void {
    this.errorMessage = '';
    this.successMessage = '';

    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    const formVals = this.registerForm.value;

    this.authService
      .register({
        full_name: formVals.fullName.trim(),
        email: formVals.email.trim(),
        phone: formVals.phone.trim(),
        password: formVals.password,
        dob: formVals.dob || undefined,
      })
      .subscribe({
        next: () => {
          this.successMessage = 'Account created successfully! Signing you in...';
          // Auto login after registration
          this.authService
            .login({
              email: formVals.email.trim(),
              password: formVals.password,
              remember_me: true,
            })
            .subscribe({
              next: () => {
                this.isLoading = false;
                this.router.navigate(['/dashboard']);
              },
              error: () => {
                this.isLoading = false;
                this.router.navigate(['/login']);
              },
            });
        },
        error: (err: Error) => {
          this.isLoading = false;
          this.errorMessage = err.message || 'Registration failed. Please check your information.';
        },
      });
  }
}
