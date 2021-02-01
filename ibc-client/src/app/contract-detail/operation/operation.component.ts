import { Component, OnChanges, Input } from '@angular/core';

@Component({
  selector: 'app-operation',
  templateUrl: './operation.component.html',
  styleUrls: ['./operation.component.css']
})
export class OperationComponent implements OnChanges {

  constructor() { }

  @Input() name: string;
  @Input() method: string;
  @Input() arguments: string[];

  values: string[];

  ngOnChanges(): void {
    this.values = new Array(this.arguments.length);
  }

  call(): void {
    console.log(this.values);
  }
}
