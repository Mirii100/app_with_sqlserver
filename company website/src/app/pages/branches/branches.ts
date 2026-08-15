import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface Branch {
  name: string;
  address: string;
  phone: string;
  hours: string;
  services: string[];
  map: string;
}

@Component({
  selector: 'app-branches',
  imports: [CommonModule, RouterLink],
  templateUrl: './branches.html',
  styleUrl: './branches.scss',
})
export class Branches {
  branches: Branch[] = [
    {
      name: 'Head Office – Nairobi CBD',
      address: 'Alexia Plaza, Moi Avenue, P.O. Box 1234-00100 Nairobi',
      phone: '+254 700 000 111',
      hours: 'Mon–Fri: 8:00am – 5:00pm, Sat: 9:00am – 1:00pm',
      services: ['Full banking', 'Loans & credit', 'Corporate desk', 'Diaspora services'],
      map: 'https://www.google.com/maps?q=Moi+Avenue+Nairobi&output=embed',
    },
    {
      name: 'Westlands Branch',
      address: 'Delta Centre, Ring Road, Westlands',
      phone: '+254 700 000 222',
      hours: 'Mon–Fri: 8:30am – 5:00pm, Sat: 9:00am – 1:00pm',
      services: ['Full banking', 'Business accounts', 'ATMs'],
      map: 'https://www.google.com/maps?q=Westlands+Nairobi&output=embed',
    },
    {
      name: 'Mombasa Branch',
      address: 'Mbaraki Road, Mombasa',
      phone: '+254 700 000 333',
      hours: 'Mon–Fri: 8:00am – 5:00pm, Sat: 9:00am – 1:00pm',
      services: ['Full banking', 'Chama services', 'Asset finance desk'],
      map: 'https://www.google.com/maps?q=Mbaraki+Mombasa&output=embed',
    },
    {
      name: 'Kisumu Branch',
      address: 'Oginga Odinga Street, Kisumu',
      phone: '+254 700 000 444',
      hours: 'Mon–Fri: 8:00am – 5:00pm, Sat: 9:00am – 1:00pm',
      services: ['Full banking', 'SME lending', 'Remittances'],
      map: 'https://www.google.com/maps?q=Oginga+Odinga+Street+Kisumu&output=embed',
    },
  ];
}
