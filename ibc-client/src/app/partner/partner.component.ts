import { Component, OnInit } from '@angular/core';
import { ContractService } from '../contract.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-partner',
  templateUrl: './partner.component.html',
  styleUrls: ['./partner.component.css']
})
export class PartnerComponent implements OnInit {

  agent: string;
  address: string;
  pid: string;
  name: string;

  constructor(
    private route: ActivatedRoute,
    private contractService: ContractService) { }

  ngOnInit(): void {
    this.agent = this.route.snapshot.paramMap.get('agent');
  }

  connect(): void {
    this.contractService.connect(this.agent, this.address, this.pid, this.name)
      .subscribe();
  }
}
