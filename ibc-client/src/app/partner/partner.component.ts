import { Component, OnInit } from '@angular/core';
import { ContractService } from '../contract.service';

@Component({
  selector: 'app-partner',
  templateUrl: './partner.component.html',
  styleUrls: ['./partner.component.css']
})
export class PartnerComponent implements OnInit {

  address: string;
  pid: string;
  name: string;

  constructor(private contractService: ContractService) { }

  ngOnInit(): void {
  }

  connect(): void {
    this.contractService.connect(this.address, this.pid, this.name)
      .subscribe();
  }
}
