import { Injectable, ErrorHandler } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class GlobalErrorHandler implements ErrorHandler {
  handleError(error: any): void {
    // In a real app, you might log this to a server
    console.error('An error occurred:', error);
    
    // For now, let's keep it simple with a user-friendly console message
    // Later, this can trigger a toast notification service
  }
}
