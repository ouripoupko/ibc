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

  constructor(
    private route: ActivatedRoute,
    private contractService: ContractService,
    private location: Location
  ) {}

  ngOnInit(): void {
    this.getContract()
  }

  getContract(): void {
    const name = this.route.snapshot.paramMap.get('name');
    this.contractService.getContract(name).subscribe(contract => this.contract = contract);
  }

  save(): void {
    this.contractService.updateContract(this.contract)
      .subscribe(() => this.goBack());
  }

  goBack(): void {
    this.location.back();
  }
}