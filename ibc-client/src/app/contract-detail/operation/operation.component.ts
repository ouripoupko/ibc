import { Component, OnChanges, Input } from '@angular/core';

import { ContractService } from '../../contract.service';
import { Contract, Method } from '../../contract';

@Component({
  selector: 'app-operation',
  templateUrl: './operation.component.html',
  styleUrls: ['./operation.component.css']
})
export class OperationComponent implements OnChanges {

  constructor(
    private contractService: ContractService
  ) { }

  @Input() name: string;
  @Input() method: string;
  @Input() arguments: string[];

  values: string[];

  ngOnChanges(): void {
    this.values = new Array(this.arguments.length);
  }

  call(): void {
    this.contractService.callContract( this.name, { name: this.method, values: this.values} as Method)
      .subscribe();
  }
}
