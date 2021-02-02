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

  constructor(
    private route: ActivatedRoute,
    private contractService: ContractService,
    private location: Location
  ) {}

  ngOnInit(): void {
    this.getContract()
  }

  getContract(): void {
    this.name = this.route.snapshot.paramMap.get('name');
    this.contractService.getContract(this.name).subscribe(contract => this.contract = contract);
  }

  goBack(): void {
    this.location.back();
  }
}
