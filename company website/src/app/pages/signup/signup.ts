import { Component } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { AuthService, SignupPayload } from '../../services/auth/auth.service';

@Component({
  selector: 'app-signup',
  imports: [ReactiveFormsModule, CommonModule, RouterLink],
  templateUrl: './signup.html',
  styleUrl: './signup.scss',
})
export class Signup {
  signupForm: FormGroup;
  submitting = false;
  serverError: string | null = null;
  fieldErrors: Record<string, string> = {};
  success: { name: string; accountNumber: string } | null = null;

  counties = [
    'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo-Marakwet', 'Embu', 'Garissa', 'Homa Bay',
    'Isiolo', 'Kajiado', 'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga', 'Kisii',
    'Kisumu', 'Kitui', 'Kwale', 'Laikipia', 'Lamu', 'Machakos', 'Makueni', 'Mandera',
    'Marsabit', 'Meru', 'Migori', 'Mombasa', 'Murang\'a', 'Nairobi', 'Nakuru', 'Nandi',
    'Narok', 'Nyamira', 'Nyandarua', 'Nyeri', 'Samburu', 'Siaya', 'Taita-Taveta', 'Tana River',
    'Tharaka-Nithi', 'Trans-Nzoia', 'Turkana', 'Uasin Gishu', 'Vihiga', 'Wajir', 'West Pokot',
  ];

  employmentTypes = ['Employed (Salaried)', 'Self-Employed', 'Business Owner', 'Casual Worker', 'Retired', 'Student', 'Other'];

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.signupForm = this.fb.group({
      full_name: ['', Validators.required],
      username: ['', [Validators.required, Validators.minLength(3)]],
      email: ['', [Validators.required, Validators.email]],
      phone_number: ['', [Validators.required, Validators.pattern(/^(\+?254|0)?[17]\d{8}$/)]],
      national_id: ['', Validators.required],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirm_password: ['', Validators.required],
      county: ['', Validators.required],
      town: ['', Validators.required],
      postal_code: [''],
      employment_type: ['', Validators.required],
      monthly_income: ['', [Validators.required, Validators.min(0)]],
      referral_code: [''],
    }, { validators: this.passwordMatch });
  }

  passwordMatch(group: FormGroup) {
    const pass = group.get('password')?.value;
    const confirm = group.get('confirm_password')?.value;
    return pass === confirm ? null : { mismatch: true };
  }

  onSubmit() {
    if (this.signupForm.invalid || this.submitting) {
      this.signupForm.markAllAsTouched();
      return;
    }

    this.submitting = true;
    this.serverError = null;
    this.fieldErrors = {};

    const value = this.signupForm.value;
    const payload: SignupPayload = {
      username: value.username,
      email: value.email,
      password: value.password,
      phone_number: value.phone_number,
      full_name: value.full_name,
      national_id: value.national_id,
      county: value.county,
      town: value.town,
      postal_code: value.postal_code || undefined,
      employment_type: value.employment_type,
      monthly_income: Number(value.monthly_income) || 0,
    };
    if (value.referral_code) {
      payload.referral_code = value.referral_code.trim().toUpperCase();
    }

    this.authService.signup(payload).subscribe({
      next: (res) => {
        this.submitting = false;
        this.success = { name: res.full_name, accountNumber: res.account_number };
        this.signupForm.reset();
      },
      error: (err) => {
        this.submitting = false;
        if (err.status === 400 && err.error) {
          for (const [field, msgs] of Object.entries(err.error)) {
            const first = Array.isArray(msgs) ? msgs[0] : msgs;
            this.fieldErrors[field] = String(first);
          }
          this.serverError = Object.values(this.fieldErrors)[0] || 'Please correct the highlighted fields.';
        } else {
          this.serverError = 'We could not reach the server. Please try again later.';
        }
      }
    });
  }

  goToLogin() {
    this.router.navigate(['/login']);
  }
}
