import { Component, OnInit } from '@angular/core';
import { Contract } from '../contract';
import { ContractService } from '../contract.service';
import { MessageService } from '../message.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-contracts',
  templateUrl: './contracts.component.html',
  styleUrls: ['./contracts.component.css']
})
export class ContractsComponent implements OnInit {

  agent: string;
  contracts: Contract[];

  getContracts(): void {
    this.contractService.getContracts(this.agent)
      .subscribe(contracts => {this.contracts = contracts; console.log(contracts);});
  }

  constructor(
      private route: ActivatedRoute,
      private contractService: ContractService) { }

  ngOnInit(): void {
    this.agent = this.route.snapshot.paramMap.get('agent');
    this.getContracts();
  }

}
