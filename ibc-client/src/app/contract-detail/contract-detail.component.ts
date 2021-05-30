import { Component, OnInit, Input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';

import { ContractService } from '../contract.service';
import { Contract } from '../contract';

@Component({
  selector: 'app-contract-detail',
  templateUrl: './contract-detail.component.html',
  styleUrls: ['./contract-detail.component.css']
})
export class ContractDetailComponent implements OnInit {

  @Input() contract: Contract;
  name: string;
  agent: string;

  constructor(
    private route: ActivatedRoute,
    private contractService: ContractService,
    private location: Location
  ) {}

  ngOnInit(): void {
    this.agent = this.route.snapshot.paramMap.get('agent');
    this.getContract()
  }

  getContract(): void {
    this.name = this.route.snapshot.paramMap.get('name');
    this.contractService.getContract(this.agent, this.name).subscribe(contract => this.contract = contract);
  }

  updateReply(something) {
    console.log(something);
    this.getContract();
  }

  goBack(): void {
    this.location.back();
  }
  stringify(something): string {
    return JSON.stringify(something);
  }
}
