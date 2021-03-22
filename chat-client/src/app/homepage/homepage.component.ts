import { Component, OnInit } from '@angular/core';
import { Contract } from '../contract';
import { ContractService } from '../contract.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-homepage',
  templateUrl: './homepage.component.html',
  styleUrls: ['./homepage.component.css']
})
export class HomepageComponent implements OnInit {

  identities: string[];
  contracts: Contract[];

  constructor(
    private router: Router,
    private contractService: ContractService
  ) { }

  ngOnInit(): void {
  }

  onServerChange(event, stepper) {
    this.identities = null;
    this.contracts = null;
    this.contractService.getIdentities(event.option.value)
      .subscribe(identities => {this.identities = identities; stepper.next();});
  }

  onIdentityChange(event, stepper) {
    this.contracts = null;
    this.contractService.getContracts(event.option.value)
      .subscribe(contracts => {this.contracts = contracts; stepper.next();});
  }

  onContractChange(event) {
    this.contractService.setContract(event.option.value);
    this.router.navigate(['chat']);
  }

}
