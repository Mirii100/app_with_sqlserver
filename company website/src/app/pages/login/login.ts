import { Component } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { AuthService } from '../../services/auth/auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, CommonModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  loginForm: FormGroup;
  submitting = false;
  serverError: string | null = null;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.loginForm = this.fb.group({
      identifier: ['', Validators.required],
      password: ['', Validators.required],
    });
  }

  onSubmit() {
    if (this.loginForm.invalid || this.submitting) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.submitting = true;
    this.serverError = null;

    const { identifier, password } = this.loginForm.value;

    this.authService.loginWithCredentials(identifier.trim(), password).subscribe({
      next: () => {
        this.submitting = false;
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.submitting = false;
        if (err.status === 400 && err.error?.detail) {
          this.serverError = err.error.detail;
        } else {
          this.serverError = 'Unable to log in. Please check your details and try again.';
        }
      }
    });
  }
}
