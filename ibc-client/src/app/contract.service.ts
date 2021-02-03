import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { Contract, Method } from './contract';
import { MessageService } from './message.service';

@Injectable({
  providedIn: 'root'
})
export class ContractService {

  private contractUrl = 'contract';
  httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' })
  };

  constructor(
    private http: HttpClient,
    private messageService: MessageService) { }

  private log(message: string) {
    this.messageService.add(`contractService: ${message}`);
  }

  /** GET **/
  getContracts(): Observable<Contract[]> {
    return this.http.get<Contract[]>(this.contractUrl)
      .pipe(
        tap(_ => this.log('fetched contracts')),
        catchError(this.handleError<Contract[]>('getContracts', []))
      );
  }

  /** GET **/
  getContract(name: string): Observable<Contract> {
    const url = `${this.contractUrl}/${name}`;
    return this.http.get<Contract>(url).pipe(
      tap((newContract: Contract) => console.log(newContract)), //_ => this.log(`fetched contract name=${name}`); console.log(_);),
      catchError(this.handleError<Contract>(`getContract name=${name}`))
    );
  }

  /** PUT **/
  callContract(name: string, method: Method): Observable<any> {
    const url = `${this.contractUrl}/${name}`;
    return this.http.put(url, method, this.httpOptions).pipe(
      tap(_ => this.log(`called contract name=${name} method=${method.name}`)),
      catchError(this.handleError<any>('callContract'))
    );
  }

  /** POST **/
  addContract(contract: Contract): Observable<Contract> {
    return this.http.post<Contract>(`${this.contractUrl}/${contract.name}`, contract, this.httpOptions).pipe(
      tap((newContract: Contract) => this.log(`added contract with name=${newContract.name}`)),
      catchError(this.handleError<Contract>('addContract'))
    );
  }

  /** POST **/
  connect(address: string, pid: string, name: string): Observable<Contract> {
    return this.http.post(`partner/${name}`, { address: address, pid: pid }, this.httpOptions).pipe(
      tap(_ => this.log(`connected to ${address} with contract ${name}`)),
      catchError(this.handleError<any>('connect'))
    );
  }

  /**
   * Handle Http operation that failed.
   * Let the app continue.
   * @param operation - name of the operation that failed
   * @param result - optional value to return as the observable result
  */
  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {

      // TODO: send the error to remote logging infrastructure
      console.error(error); // log to console instead

      // TODO: better job of transforming error for user consumption
      this.log(`${operation} failed: ${error.message}`);

      // Let the app keep running by returning an empty result.
      return of(result as T);
    };
  }
}
